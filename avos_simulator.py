from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import random
from typing import Deque, Dict, List, Optional, Tuple

try:
    import pygame
except ImportError:  # GUI optional dependency
    pygame = None


@dataclass
class Process:
    name: str
    base_priority: int
    state: str = "Ready"  # Ready, Running, Blocked, Terminated
    inherited_priority: int = 0
    io_block_until: Optional[int] = None

    @property
    def effective_priority(self) -> int:
        return max(self.base_priority, self.inherited_priority)

    def block_for_io(self, until_cycle: int) -> None:
        self.state = "Blocked"
        self.io_block_until = until_cycle


class MapDataLock:
    def __init__(self) -> None:
        self.owner: Optional[str] = None
        self.waiting: Deque[str] = deque()


class PagingMemory:
    """16-page virtual memory with LRU replacement."""

    def __init__(self, virtual_pages: int = 16, physical_frames: int = 4) -> None:
        self.virtual_pages = virtual_pages
        self.physical_frames = physical_frames
        self.page_table: Dict[int, int] = {}  # virtual_page -> frame
        self.frame_to_page: Dict[int, int] = {}  # frame -> virtual_page
        self.last_used: Dict[int, int] = {}  # virtual_page -> cycle
        self.next_frame = 0
        self.memory_exhausted = False

    def translate(self, virtual_address: int, cycle: int) -> Tuple[Optional[int], List[str]]:
        logs: List[str] = []
        page = virtual_address // 256
        offset = virtual_address % 256
        if page >= self.virtual_pages:
            logs.append(f"Geçersiz adres {virtual_address} (Sayfa {page})")
            return None, logs

        if page not in self.page_table:
            logs.append(f"Page Fault! Sayfa {page} RAM'de değil.")
            if self.memory_exhausted:
                logs.append("Memory Exhaustion: Yeni frame ayrılamıyor.")
                return None, logs
            self._load_page(page, cycle, logs)

        self.last_used[page] = cycle
        frame = self.page_table[page]
        physical_address = frame * 256 + offset
        logs.append(f"VA {virtual_address} -> PA {physical_address} (P{page}->F{frame})")
        return physical_address, logs

    def _load_page(self, page: int, cycle: int, logs: List[str]) -> None:
        if len(self.page_table) < self.physical_frames:
            frame = self.next_frame
            self.next_frame += 1
            self.page_table[page] = frame
            self.frame_to_page[frame] = page
            logs.append(f"Page {page} yüklendi (Frame {frame}).")
        else:
            victim = min(self.last_used, key=self.last_used.get)
            victim_frame = self.page_table[victim]
            del self.page_table[victim]
            del self.last_used[victim]
            self.page_table[page] = victim_frame
            self.frame_to_page[victim_frame] = page
            logs.append(
                f"LRU: Page {victim} çıkarıldı, Page {page} Frame {victim_frame}'e yüklendi."
            )
        self.last_used[page] = cycle


class AVOSSimulator:
    def __init__(self, total_cycles: int = 16) -> None:
        self.total_cycles = total_cycles
        self.cycle = 0
        self.distance = 0
        self.last_running: Optional[str] = None
        self.scheduler_mode = "FIFO"
        self.memory = PagingMemory(virtual_pages=16, physical_frames=4)
        self.map_lock = MapDataLock()
        self.processes: Dict[str, Process] = {
            "Lidar_Sensor": Process("Lidar_Sensor", 3),
            "Path_Planner": Process("Path_Planner", 2),
            "Emergency_Brake": Process("Emergency_Brake", 5),
            "Infotainment_System": Process("Infotainment_System", 1),
        }
        self.fifo_queue: Deque[str] = deque(
            ["Lidar_Sensor", "Path_Planner", "Infotainment_System", "Emergency_Brake"]
        )
        self.ready_set = set(self.fifo_queue)
        self.current_running: Optional[str] = None
        self.oom_triggered = False
        self.history: List[str] = []

    def run(self) -> None:
        print("=== AVOS (Autonomous Vehicle Operating System) Simülasyonu ===")
        while self.cycle < self.total_cycles:
            log_line, _, _, _ = self.step()
            print(log_line)

    def step(self) -> Tuple[str, Optional[str], List[str], bool]:
        self.cycle += 1
        event_logs: List[str] = []
        memory_logs: List[str] = []

        self.distance += 1
        self._scripted_events(event_logs)
        self._unblock_io(event_logs)

        running = self._pick_next_process(event_logs)
        self.current_running = running

        if running:
            self.processes[running].state = "Running"
            memory_logs.extend(self._process_memory_activity(running))
            self._post_run_state_update(running)
        else:
            event_logs.append("CPU Idle")

        log_line = self._format_observability_log(running, event_logs, memory_logs)
        self.history.append(log_line)
        self.last_running = running
        memory_exhaustion_alert = any("Memory Exhaustion" in msg for msg in event_logs + memory_logs)
        return log_line, running, event_logs + memory_logs, memory_exhaustion_alert

    def _scripted_events(self, event_logs: List[str]) -> None:
        # Baseline FIFO phase
        if self.cycle == 2:
            lidar = self.processes["Lidar_Sensor"]
            if lidar.state != "Terminated":
                lidar.block_for_io(self.cycle + 2)
                event_logs.append("Lidar_Sensor I/O bekliyor -> Blocked")
                self._remove_from_ready("Lidar_Sensor")

        # Engineering challenge: priority inversion setup
        if self.cycle == 3 and self.map_lock.owner is None:
            self.map_lock.owner = "Infotainment_System"
            event_logs.append("Infotainment_System Harita Verisi kilidini aldı")

        # Switch to enhanced scheduler
        if self.cycle == 5:
            self.scheduler_mode = "PRIORITY_PREEMPTIVE"
            event_logs.append("Scheduler modu değişti: FIFO -> Priority Preemptive")

        # High priority process waits for low priority lock
        if self.cycle == 6:
            self._request_map_lock("Emergency_Brake", event_logs)

        # Lock owner eventually releases, inheritance resolves inversion
        if self.cycle == 7 and self.map_lock.owner == "Infotainment_System":
            self._release_map_lock("Infotainment_System", event_logs)

        # Required failure scenario
        if self.cycle == 10 and not self.oom_triggered:
            self.memory.memory_exhausted = True
            event_logs.append("Memory Exhaustion simülasyonu tetiklendi")
            self._oom_kill_lowest_priority(event_logs)
            self.oom_triggered = True

    def _unblock_io(self, event_logs: List[str]) -> None:
        for p in self.processes.values():
            if p.state == "Blocked" and p.io_block_until and self.cycle >= p.io_block_until:
                p.state = "Ready"
                p.io_block_until = None
                self._add_to_ready(p.name)
                event_logs.append(f"{p.name} I/O tamamladı -> Ready")

    def _request_map_lock(self, requester: str, event_logs: List[str]) -> None:
        proc = self.processes[requester]
        if self.map_lock.owner is None:
            self.map_lock.owner = requester
            event_logs.append(f"{requester} Harita Verisi kilidini aldı")
            return

        owner = self.map_lock.owner
        self.map_lock.waiting.append(requester)
        proc.state = "Blocked"
        self._remove_from_ready(requester)
        event_logs.append(f"{requester} Harita Verisi için beklemede (Blocked)")
        if owner:
            owner_proc = self.processes[owner]
            if owner_proc.effective_priority < proc.effective_priority:
                owner_proc.inherited_priority = proc.effective_priority
                event_logs.append(
                    f"Priority Inheritance: {owner} önceliği {owner_proc.effective_priority} oldu"
                )

    def _release_map_lock(self, owner: str, event_logs: List[str]) -> None:
        if self.map_lock.owner != owner:
            return
        owner_proc = self.processes[owner]
        owner_proc.inherited_priority = 0
        event_logs.append(f"{owner} Harita Verisi kilidini bıraktı")
        self.map_lock.owner = None

        if self.map_lock.waiting:
            next_owner = self.map_lock.waiting.popleft()
            waiter = self.processes[next_owner]
            waiter.state = "Ready"
            self._add_to_ready(next_owner)
            self.map_lock.owner = next_owner
            event_logs.append(f"{next_owner} kilidi devraldı ve Ready oldu")

    def _oom_kill_lowest_priority(self, event_logs: List[str]) -> None:
        alive = [p for p in self.processes.values() if p.state != "Terminated"]
        if not alive:
            return
        victim = min(alive, key=lambda p: p.base_priority)
        victim.state = "Terminated"
        self._remove_from_ready(victim.name)
        if self.current_running == victim.name:
            self.current_running = None
        event_logs.append(f"OOM Killer: {victim.name} sonlandırıldı")

    def _pick_next_process(self, event_logs: List[str]) -> Optional[str]:
        if self.scheduler_mode == "FIFO":
            return self._pick_fifo(event_logs)
        return self._pick_priority_preemptive(event_logs)

    def _pick_fifo(self, event_logs: List[str]) -> Optional[str]:
        for _ in range(len(self.fifo_queue)):
            candidate = self.fifo_queue.popleft()
            self.fifo_queue.append(candidate)
            p = self.processes[candidate]
            if p.state == "Ready":
                if self.last_running and self.last_running != candidate:
                    event_logs.append(f"Context Switch: {self.last_running} -> {candidate}")
                return candidate
        return None

    def _pick_priority_preemptive(self, event_logs: List[str]) -> Optional[str]:
        ready = [p for p in self.processes.values() if p.state == "Ready"]
        if not ready:
            return None
        ready.sort(key=lambda p: (-p.effective_priority, p.name))
        selected = ready[0].name
        if self.last_running and self.last_running != selected:
            event_logs.append(f"Preemptive Context Switch: {self.last_running} -> {selected}")
        return selected

    def _process_memory_activity(self, running: str) -> List[str]:
        # Different access patterns force page-fault/LRU events visibly.
        patterns = {
            "Lidar_Sensor": [130, 420, 820, 1220],
            "Path_Planner": [560, 960, 1360, 1760],
            "Emergency_Brake": [40, 300, 680, 940],
            "Infotainment_System": [2000, 2300, 2600, 2900],
        }
        arr = patterns[running]
        va = arr[(self.cycle - 1) % len(arr)]
        _, logs = self.memory.translate(va, self.cycle)
        return logs

    def _post_run_state_update(self, running: str) -> None:
        p = self.processes[running]
        if p.state == "Running":
            p.state = "Ready"
            self._add_to_ready(running)

    def _add_to_ready(self, name: str) -> None:
        if name in self.processes and self.processes[name].state != "Terminated":
            self.ready_set.add(name)

    def _remove_from_ready(self, name: str) -> None:
        if name in self.ready_set:
            self.ready_set.remove(name)

    def _road_bar(self) -> str:
        width = 12
        pos = min(self.distance, width)
        return "[" + "=" * pos + ">" + " " * (width - pos) + "]"

    def _print_observability_log(
        self, running: Optional[str], scheduler_logs: List[str], memory_logs: List[str]
    ) -> None:
        print(self._format_observability_log(running, scheduler_logs, memory_logs))

    def _format_observability_log(
        self, running: Optional[str], scheduler_logs: List[str], memory_logs: List[str]
    ) -> str:
        scheduler_text = (
            f"{running} çalışıyor" if running else "Idle"
        )
        if scheduler_logs:
            scheduler_text += " | " + " ; ".join(scheduler_logs)
        memory_text = " ; ".join(memory_logs) if memory_logs else "Bellek olayı yok"
        return (
            f"[ROBOT-OS] \U0001f697 Yol: {self._road_bar()} | "
            f"[Scheduler]: {scheduler_text} | [Memory]: {memory_text}"
        )


class AVOSGui:
    def __init__(self, simulator: AVOSSimulator) -> None:
        if pygame is None:
            raise RuntimeError("pygame yüklü değil. `pip install pygame` ile yükleyin.")
        self.simulator = simulator
        self.width = 1200
        self.height = 680
        self.road_width = 700
        self.log_panel_x = 720
        self.log_lines: Deque[str] = deque(maxlen=26)
        self.alert_blink = False
        self.alert_ticks = 0
        self.last_step_ms = 0
        self.step_interval_ms = 850
        self.road_scroll = 0.0
        self.current_progress = 0.0
        self.target_progress = 0.0
        self.car_x = 58.0
        self.car_y = float(self.height // 2 - 34)
        self.target_car_y = self.car_y
        self.current_process_label = "Idle"
        self.drive_mode = "AUTONOMOUS"  # AUTONOMOUS or MANUAL
        self.manual_lane_index = 1
        self.manual_speed_boost = 0.0
        self.manual_x_offset = 0.0
        self.pressed_keys = {"left": False, "right": False, "up": False, "down": False}
        self.brake_pressed = False
        self.obstacles: List[Dict[str, float]] = []
        self.autonomous_avoid_cooldown = 0
        self.collision_flash_ticks = 0
        self.proximity_alert_active = False
        self.proximity_alert_ticks = 0
        self.proximity_threshold = 120.0
        # Running process -> lane mapping for visible lane changes.
        self.lane_map = {
            "Emergency_Brake": 180,
            "Lidar_Sensor": 285,
            "Path_Planner": 390,
            "Infotainment_System": 495,
        }
        self.lane_centers = [180.0, 285.0, 390.0, 495.0]
        self.max_track_progress = 0.86

        pygame.init()
        pygame.display.set_caption("AVOS 2D GUI - Autonomous Vehicle OS Simulator")
        self.screen = pygame.display.set_mode((self.width, self.height))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("consolas", 18)
        self.small_font = pygame.font.SysFont("consolas", 15)
        self.big_font = pygame.font.SysFont("consolas", 28, bold=True)

    def run(self) -> None:
        running = True
        sim_finished = False
        while running:
            now = pygame.time.get_ticks()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN:
                    self._on_key_change(event.key, True)
                if event.type == pygame.KEYUP:
                    self._on_key_change(event.key, False)

            if not sim_finished and now - self.last_step_ms >= self.step_interval_ms:
                line, current_proc, details, memory_alert = self.simulator.step()
                self.last_step_ms = now
                self.target_progress = min(
                    self.simulator.distance / max(1, self.simulator.total_cycles), 1.0
                )
                self.current_process_label = current_proc or "Idle"
                if self.drive_mode == "AUTONOMOUS" and current_proc in self.lane_map:
                    self.target_car_y = float(self.lane_map[current_proc] - 34)
                self.log_lines.appendleft(line)
                if current_proc:
                    self.log_lines.appendleft(f"-> Running: {current_proc}")
                for item in details:
                    self.log_lines.appendleft(f"   - {item}")
                if memory_alert:
                    self.alert_blink = True
                    self.alert_ticks = 18
                if self.simulator.cycle >= self.simulator.total_cycles:
                    sim_finished = True
                    self.log_lines.appendleft("=== Simülasyon tamamlandı ===")

            self._draw_scene()
            pygame.display.flip()
            self.clock.tick(60)

        pygame.quit()

    def _draw_scene(self) -> None:
        self.screen.fill((18, 18, 20))
        self._update_animation()
        self._draw_road()
        self._draw_car()
        self._draw_logs_panel()
        self._draw_memory_alert()

    def _on_key_change(self, key: int, is_down: bool) -> None:
        if key == pygame.K_m and is_down:
            self.drive_mode = "MANUAL" if self.drive_mode == "AUTONOMOUS" else "AUTONOMOUS"
            self.log_lines.appendleft(f"[INPUT] Mode switched to {self.drive_mode}")
            if self.drive_mode == "MANUAL":
                self.manual_lane_index = self._closest_lane_index()
        elif key in (pygame.K_LEFT, pygame.K_a):
            self.pressed_keys["left"] = is_down
        elif key in (pygame.K_RIGHT, pygame.K_d):
            self.pressed_keys["right"] = is_down
        elif key in (pygame.K_UP, pygame.K_w):
            self.pressed_keys["up"] = is_down
        elif key in (pygame.K_DOWN, pygame.K_s):
            self.pressed_keys["down"] = is_down
        elif key == pygame.K_o and is_down:
            self._spawn_obstacle()
        elif key == pygame.K_SPACE:
            self.brake_pressed = is_down

    def _closest_lane_index(self) -> int:
        center_y = self.car_y + 34.0
        return min(range(len(self.lane_centers)), key=lambda i: abs(self.lane_centers[i] - center_y))

    def _update_animation(self) -> None:
        # Smoothly animate forward progress and lane changes between OS ticks.
        self.current_progress += (self.target_progress - self.current_progress) * 0.12
        self.current_progress = min(self.current_progress, self.max_track_progress)
        self._handle_drive_inputs()
        self._handle_obstacle_avoidance()
        self.car_y += (self.target_car_y - self.car_y) * 0.16
        start_x = 58
        end_x = self.road_width - 150
        track_end_x = start_x + (end_x - start_x) * self.max_track_progress
        base_x = start_x + (track_end_x - start_x) * self.current_progress
        # Keep only forward cap; reverse side is intentionally unbounded by request.
        self.car_x = min(track_end_x, base_x + self.manual_x_offset)
        # Keep road flow independent from braking so the road never "freezes".
        self.road_scroll = (self.road_scroll + 3.5) % 52
        self._update_obstacles()
        if self.autonomous_avoid_cooldown > 0:
            self.autonomous_avoid_cooldown -= 1
        if self.collision_flash_ticks > 0:
            self.collision_flash_ticks -= 1
        if self.proximity_alert_ticks > 0:
            self.proximity_alert_ticks -= 1

    def _handle_drive_inputs(self) -> None:
        if self.drive_mode != "MANUAL":
            self.manual_speed_boost *= 0.92
            return

        changed_lane = False
        if self.pressed_keys["left"]:
            self.manual_lane_index = max(0, self.manual_lane_index - 1)
            self.pressed_keys["left"] = False
            changed_lane = True
        if self.pressed_keys["right"]:
            self.manual_lane_index = min(len(self.lane_centers) - 1, self.manual_lane_index + 1)
            self.pressed_keys["right"] = False
            changed_lane = True
        if changed_lane:
            self.target_car_y = self.lane_centers[self.manual_lane_index] - 34.0
            self.log_lines.appendleft(f"[MANUAL] Lane -> {self.manual_lane_index + 1}")

        if self.pressed_keys["up"]:
            self.manual_speed_boost = min(4.0, self.manual_speed_boost + 0.15)
            self.manual_x_offset = min(140.0, self.manual_x_offset + 2.1)
        elif self.pressed_keys["down"]:
            self.manual_speed_boost = max(-2.0, self.manual_speed_boost - 0.15)
            self.manual_x_offset -= 2.1
        else:
            self.manual_speed_boost *= 0.92

        if self.brake_pressed:
            self.manual_speed_boost = max(-4.0, self.manual_speed_boost - 0.32)
            self.manual_x_offset -= 1.1

    def _spawn_obstacle(self) -> None:
        lane = random.choice(self.lane_centers)
        obstacle = {
            "x": float(self.road_width - 52),
            "y": float(lane),
            "w": 44.0,
            "h": 34.0,
            "speed": random.uniform(1.8, 4.2),
        }
        self.obstacles.append(obstacle)
        self.log_lines.appendleft(f"[PERCEPTION] Obstacle spawned on lane y={int(lane)}")

    def _handle_obstacle_avoidance(self) -> None:
        nearest = self._nearest_obstacle_in_lane()
        if nearest is None:
            self.proximity_alert_active = False
            return

        dist = nearest["x"] - (self.car_x + 52.0)
        in_danger = dist < self.proximity_threshold
        if in_danger and not self.proximity_alert_active:
            self.proximity_alert_ticks = 20
            self.log_lines.appendleft(
                f"[ALERT] Proximity warning! Obstacle distance={int(max(0.0, dist))}"
            )
        elif in_danger:
            self.proximity_alert_ticks = max(self.proximity_alert_ticks, 2)
        self.proximity_alert_active = in_danger
        if self.drive_mode == "AUTONOMOUS":
            if dist < 140 and self.autonomous_avoid_cooldown == 0:
                target = self._find_clear_lane()
                if target is not None:
                    self.target_car_y = target - 34.0
                    self.autonomous_avoid_cooldown = 36
                    self.log_lines.appendleft("[AUTONOMOUS] Obstacle detected -> lane change")
                else:
                    self.manual_speed_boost = max(-4.5, self.manual_speed_boost - 0.25)
                    self.autonomous_avoid_cooldown = 18
                    self.log_lines.appendleft("[AUTONOMOUS] No clear lane -> braking")
        elif self.brake_pressed:
            self.manual_speed_boost = max(-5.0, self.manual_speed_boost - 0.35)

    def _nearest_obstacle_in_lane(self) -> Optional[Dict[str, float]]:
        car_center_y = self.car_y + 34.0
        nearest = None
        min_dist = 10_000.0
        for ob in self.obstacles:
            if abs(ob["y"] - car_center_y) > 34:
                continue
            dist = ob["x"] - (self.car_x + 52.0)
            if 0 < dist < min_dist:
                min_dist = dist
                nearest = ob
        return nearest

    def _find_clear_lane(self) -> Optional[float]:
        car_front_x = self.car_x + 52.0
        car_center_y = self.car_y + 34.0
        lanes = sorted(self.lane_centers, key=lambda y: abs(y - car_center_y))
        for lane in lanes:
            if abs(lane - car_center_y) < 8:
                continue
            blocked = False
            for ob in self.obstacles:
                if abs(ob["y"] - lane) > 28:
                    continue
                if -40 < (ob["x"] - car_front_x) < 165:
                    blocked = True
                    break
            if not blocked:
                return lane
        return None

    def _update_obstacles(self) -> None:
        base_speed = 2.8 + max(0.0, self.manual_speed_boost * 0.35)
        # Brake should mostly stop the car relative motion, not the road animation.
        speed = base_speed * (0.18 if self.brake_pressed else 1.0)
        keep: List[Dict[str, float]] = []
        car_rect = pygame.Rect(int(self.car_x), int(self.car_y + 4), 90, 44)
        for ob in self.obstacles:
            ob["x"] -= speed - ob["speed"] * 0.35
            ob_rect = pygame.Rect(int(ob["x"]), int(ob["y"] - ob["h"] / 2), int(ob["w"]), int(ob["h"]))
            if ob_rect.right < 30:
                continue
            if ob_rect.colliderect(car_rect):
                self.collision_flash_ticks = 18
                self.manual_speed_boost = -5.0
                self.log_lines.appendleft("[CRITICAL] Collision! Use SPACE brake / lane escape.")
                continue
            keep.append(ob)
        self.obstacles = keep

    def _draw_road(self) -> None:
        pygame.draw.rect(self.screen, (60, 60, 68), (30, 120, self.road_width - 60, 440), border_radius=12)
        lane_positions = [180, 285, 390, 495]
        for y in lane_positions:
            pygame.draw.line(self.screen, (76, 76, 86), (42, y), (self.road_width - 40, y), 2)
        dash_width = 42
        for lane_y in lane_positions:
            for i in range(14):
                x = int(58 + i * 52 - self.road_scroll)
                pygame.draw.rect(self.screen, (230, 230, 230), (x, lane_y - 5, dash_width, 10))
        title = self.big_font.render("AVOS Highway", True, (240, 240, 240))
        self.screen.blit(title, (40, 40))
        subtitle = self.small_font.render(
            "M: mode | O: obstacle | A/D or <-/->: lane | SPACE: brake | W/S: throttle",
            True,
            (190, 198, 210),
        )
        self.screen.blit(subtitle, (44, 78))
        for ob in self.obstacles:
            rect = pygame.Rect(int(ob["x"]), int(ob["y"] - ob["h"] / 2), int(ob["w"]), int(ob["h"]))
            pygame.draw.rect(self.screen, (240, 82, 82), rect, border_radius=6)
            pygame.draw.rect(self.screen, (255, 240, 240), rect, 2, border_radius=6)

    def _draw_car(self) -> None:
        car_x = int(self.car_x)
        car_y = int(self.car_y)

        base_color = (30, 144, 255) if self.collision_flash_ticks % 4 > 1 else (255, 120, 90)
        # Minimal car icon shape (2D rectangle-based sprite)
        pygame.draw.rect(self.screen, base_color, (car_x, car_y + 16, 90, 32), border_radius=8)
        pygame.draw.rect(self.screen, (90, 180, 255), (car_x + 20, car_y, 50, 22), border_radius=7)
        pygame.draw.circle(self.screen, (20, 20, 20), (car_x + 20, car_y + 50), 10)
        pygame.draw.circle(self.screen, (20, 20, 20), (car_x + 70, car_y + 50), 10)
        label = self.small_font.render("CAR", True, (12, 12, 12))
        self.screen.blit(label, (car_x + 32, car_y + 20))
        proc = self.small_font.render(f"Process: {self.current_process_label}", True, (255, 255, 255))
        self.screen.blit(proc, (car_x - 4, car_y - 24))
        mode = self.small_font.render(f"Drive Mode: {self.drive_mode}", True, (255, 220, 120))
        self.screen.blit(mode, (42, 586))
        brake = self.small_font.render(
            f"Brake: {'ON' if self.brake_pressed else 'OFF'}", True, (255, 180, 180)
        )
        self.screen.blit(brake, (240, 586))

    def _draw_logs_panel(self) -> None:
        pygame.draw.rect(self.screen, (28, 30, 35), (self.log_panel_x, 20, 460, 640), border_radius=10)
        header = self.big_font.render("OS Logs", True, (255, 255, 255))
        self.screen.blit(header, (self.log_panel_x + 20, 30))

        if not self.log_lines:
            warmup = self.font.render("Simülasyon başlatılıyor...", True, (200, 200, 210))
            self.screen.blit(warmup, (self.log_panel_x + 20, 85))
            return

        y = 84
        for line in self.log_lines:
            clipped = line if len(line) <= 56 else line[:56] + "..."
            text = self.small_font.render(clipped, True, (210, 220, 235))
            self.screen.blit(text, (self.log_panel_x + 14, y))
            y += 22
            if y > 635:
                break

    def _draw_memory_alert(self) -> None:
        if self.alert_ticks <= 0:
            self.alert_blink = False
        else:
            self.alert_ticks -= 1
            if self.alert_ticks % 2 == 0:
                warning = self.big_font.render("MEMORY EXHAUSTION!", True, (255, 60, 60))
                self.screen.blit(warning, (180, 585))

        if self.proximity_alert_active and self.proximity_alert_ticks % 2 == 0:
            near_warning = self.big_font.render("PROXIMITY ALERT!", True, (255, 40, 40))
            self.screen.blit(near_warning, (200, 130))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="AVOS Simulator")
    parser.add_argument(
        "--mode",
        choices=["cli", "gui"],
        default="gui",
        help="cli: terminal log modu, gui: pygame 2D arayüz",
    )
    args = parser.parse_args()

    sim = AVOSSimulator(total_cycles=16)
    if args.mode == "cli":
        sim.run()
    else:
        try:
            AVOSGui(sim).run()
        except RuntimeError as exc:
            print(exc)
            print("CLI moduna geçiliyor...")
            sim.run()
