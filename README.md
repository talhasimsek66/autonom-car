# mini-os-simulator: Project 1

## 1. Process and Resource Manager
### Functionality:
- process : create / destroy; datastructure: PCB
- resource : request / release
- time-out interrupt : scheduling, cycle through different resources
- multi-unit resources : every unit would have more than one unit
- error checking : dealing with potential errors

### Simulation:
- without actual hardware, we simulate the process on terminal (input/output file)
	- currently running process and 
	- the hardware causing interrupts

### Organization:
- Shell
	- reads command from terminal or text file
	- invokes kernel function
	- displays reply ( termianl or output file)
		- running process
		- errors

### Workflow:
1. Input thruogh Termianl / Test Files
2. Get command wirh args, invoke command with args
3. Operates Process / Resource Manager
4. Receive response, display response

### Components:
a. Interface: 
	- termianl / test files
b. Driver:
	- looping for getting command with args (i.e. cr A 1)
	- invoking command with args
	- receive response
	- display response
c. Process/Resource Manager:

### Shell Example:
	> cr A 1 
	Process A is running 
	> cr B 2 
	Process B is running 
	> cr C 1 
	Process B is running 
	> req R1, 1 
	Process B is blocked; process A is running 



## 2. Implementation: Process
### States and Operations
- States: Ready, Running, Block
- Possible Operations:

| Ops       | State From            | State To  |
| :-------: |:---------------------:| :--------:|
| Create    | (None)                | Ready     |
| Destroy   | Running/Ready/Blocked |   (None)  |
| Request   | Running               | Blocked   |
| Release   | Blocked               | Ready     |
| Time_Out  | Running               | Ready     |
| Scheduler1| Ready                 | Running   |
| Scheduler2| Running               | Ready     |

### Process Control Block (PCB)
- PID
- Other Resources : Linked List like, pointing to resource control block, which results of requets
- Status : Type (Running/Ready/Blocked)& List (back pointer to either Ready List (if process running) Blocked List (otherwise))
- Creation Tree : Parent (pointing to parent PCB)/Child (pointing children)
- Priority : 0, 1, 2 (Init, User, System)

### Ready List
- 2 (system), 1 (user), 0 (init)
- Priorities don't change in a session
- Every process is either on Ready List or Blocked List
- When start a session, a process ties to init level to begin
- Each level of priorities may have any number of processes

### Create

	Create(initialization params) {
		create PCB data struct
		initialize PCB using params
		link PCB to creation tree
		insert(RL, PCB)
		scheduler()
	}

- Init process is created at start-up & can create first system or user process
- Any new or released process is inserted at the end of the queue (RL)

### Destroy

	Destroy (pid) {
		get pointer p to PCB using pid
		Kill_Tree(p)
		Scheduler()
	}

	Kill_Tree(p) {
		for all child processes q Kill Tree(q)
		free resources
		delete PCb and update all the pointers
	}

- Process can be destroyed by any of its ancesters or by itself (exit)



## 3. Representation of Resources
### Configuration
- There is a fixed set of resources
- Resource Control Block (RCB)
	- RID
	- Status : coutner for number of free units, K initial units (fixed), U currently available units (decreases/increases)
	- Waiting_List : list of blocked processes

### Request Resources (1-unit resource  # n-units resources)

	Request(rid) {
		r = Get_RCB(rid)
		if (r->Status == 'free') {  # u > n, where available # of units, u, and requesting # of units, n
			r->Status == 'allocated'  # u = u - n
			insert(self->Other_Resources, r)  # n units of resource r
		} else {
			self->Status.Type = 'blocked'
			self->Status.Link = r
			remove(RL, self)
			isnert(r->Waiting_List, self)
			Scheduler()
		}
	}

### Release Resources (1-unit resource  # n-units resources)

	Release(rid, n) {  # n is the number of units of resources to release
		r = Get_RCB(rid)
		remove(self->Other_Resources, r)  # u = u + n
		if (r->Waiting_list == 'NIL') {  # while (r->Waiting_List != NIL && u >= req)
			r->Status = 'free'  # u = u - req
		} else {  # ---del this line----
			remove(r->Waiting_List, q) 
			q->Status.Type = 'ready'
			q->Status.List = RL
			insert(q->Other_Resources, r)
			insert(RL, q)
			Scheduler()
		}
	}

- all requests are satisfied in strict FIFO order



## 4. Scheduling
### Specs
- 3-level priority scheduler 
- Use preemptive round-robin scheduling within level
- [Reference to preemtive round-robin scheduling](http://www.read.cs.ucla.edu/111/2007fall/notes/lec7)
- Time sharing is simulated by a function call
	- if happens, the process will be placed in the tail
- Init process serves two purposes: dummy process: lowerst priority, never blocked -root of process creation tree
- Preemption
	- Change status of p to running (status of self already changed to ready/blocked)
	- Context switch - output of nmae of running process

### Implementation

	Scheduler() {
		find highest priority process p
		if (self->priority < p->priority ||  self->Status.Type != 'running' || self == NIL)  
			premep(p, self)  # print the new running process p here
	}

	Time_out() {
		find running process p
		remove(RL, p)
		q->Status.Type = 'ready'
		insert(RL, q)
		Scheduler
	}



## 5. Presentation/Shell Script
### Mandatry Commands
- init
- cr <name> <priority>
	- name: single char
	- priority: 0, 1, or 2
- de <name>
	- name: single char
- req <resource name> <# of units>
	- resource name: R1, R2, R3, or R4
- rel <resource name> <# of units>
	- resource name: R1, R2, R3, or R4
- to
	- 'time-out'

### Optional Commands
- list all processes and its status
- list all resources and its status
- provide information about a given process
- provide information about a given resource



## 6. Summary
### Tasks
- Design/implement the process and resource manager
	- data structure and functions
- Design/implement the driver (shell)
	- command language and interpreter
- Instantiate the manager to include at a start-up:
	- A Ready List with 3 priorities
	- A single process, Init
	- 4 resources labeled: R1, R2, R3, R4 (each Ri has i units)
	- An IO resource
- Submit program for testing and documentation for evaluation

[To refer to test examples, watch this video again](http://replay.uci.edu/public/summer2013/Bic-kernel-projE_-_MP4_with_Smart_Player_(Large)_-_20130807_01.20.09AM.html)

[Official project spec](http://www.ics.uci.edu/~bic/courses/NUS-OS/PROOFS/bicpr02v2.pdf)

[Reading](http://www.ics.uci.edu/~bic/courses/NUS-OS/PROOFS/bicc04v2.pdf)

[Protocol - Make sure following this](http://www.ics.uci.edu/~bic/courses/143B/Process-Project/protocol.pdf)


## 7. Learnings
- [Python Classes Basics](https://python.swaroopch.com/oop.html)
- [Python Linked List Implementation](http://stackoverflow.com/questions/280243/python-linked-list)
- [OS Scheduling](https://www.cs.rutgers.edu/~pxk/416/notes/07-scheduling.html)
- [Deadlock Intro](http://www.cs.yale.edu/homes/aspnes/pinewiki/Deadlock.html)
- [Python Library Collections Doc](https://docs.python.org/2/library/collections.html#collections.deque)


# mini-os-simulator: Project 2
Beign project 2

## 1. Project Description A
- Goal: compare different scheduling algorithms
- assume single processor
- scheduling algo determines which process should run at each time step
- minimize turnaround time:
	- turnaround time: average of the real time of all the processes in the system
	- for all process i, sum += r_i where r_i = t_i (total time: CPU time which the process running)+ waiting time (the process not running) or finish time - start time of a process i and n = the number of processes 

## 2. Project Description B
- Implement and compere: 
	- FIFO (First-In-First-Out): Process entered first runs first
	- SJF (Shortest Job First): Process with shorter running time runs first
	- SRT (Shortest Remaining Time): SJF but preemptive. If new process has less running time than the remaining running time of currently running process, the new process runs first.
	- MLF (Multi-Level Feedback Queue): n priorities, each n level has Time Slice (TS) TS_n-1 = 2*TS_n where TS_n = 1
- Inputs: a series of arrival and total service time
- Outputs for each algorithms:
	- the real time r_i of each process
	- average turnaround time
- Output Format: T r_1 r_2 .. r_n
	- T: average turn around time
	- each r_i is the real time of process i

## 3. Testing Procedure
- For each algorithm:
	- read integer pairs ar_i (arrival time) and t_i (required running time) from file input.txt on memory stick
	- ourput results into a file name STUDENT_ID.txt to the same memory stick
- Output flie should contain 4 separate lines of the form
	- T r_1 r_2 .. r_n

## 4. References 
- [The Lecture Video including Testing Example](http://replay.uci.edu/public/winter2015/Bic-proj-schedA_-_20150112_122322_15.html)
- [Official Project Description](http://www.ics.uci.edu/~bic/courses/143B/Sched-project/Description.pdf)
- [Protocol to Follow](http://www.ics.uci.edu/~bic/courses/143B/Sched-project/Protocol.pdf)



# mini-os-simulater: Project 3

## 1. Assignment Outline
- VM using segmentatoin and paging
- managin segment and page tables in a simulated main memory 
- It accepts Virtual Addresses and translates them into Physical Addresses
- It utilizes translation look-aside buffeer (TLB) to make the process more efficient

## 2. Segmentation with Paging
![alt tag](https://cloud.githubusercontent.com/assets/1572847/23151767/2dcc602c-f7b2-11e6-9634-98ddedec7c1c.png)
 
## 3. Organization of the VM system
- Single Process -> Single Segmentation Table (ST)
- Each entry of ST points to a Paging Table (PT)
- Each entry of PT points to a program/data page
- Virtual Addrress is an integer ( 32 bits ), divided into s, p, w
	- |s| = 9: ST size is 512 words (int)
	- |p| = 10: PT size is 1024 words
	- |w| = 9: page size si 512 words (offset)
	- The leading 4 bits of VA is unused
- Each Segmentation Table (ST) entry have three types of entry:
    - -1: PT is currently not resident in PM (Page Fault)
    - 0: corresponding PT does not exist
        - read: error; write: create a blank PT
    - f: PT starts at physical address f (address, not frame #)
- Each Page Table entry have three types of entry:
    - -1: page is currently not resident in PM (Page Fault)
    - 0: corresponding page does not exist
        - read: error; write: create a blank page
    - f: page starts at physical address f

## 4. Organization of Physical Memory (PM)
- PM is represented as an array of integers
    - each corresponds to one addressable memory word
- PM is devided into frames of size 512 words (integers)
    - consequently, ST occupies one frame
    - each PT occupies two (consecutive) frames
    - each program/data page occupies one frame
- PA consists of 1024 frames (=array of 524,288 int, = 2MB)
    - consequently the size of PA is 19 bit
- ST always resides in frame 0 and is never paged out
- A page may be placed into any free frame
- A PT may be placed into any pair of consecutive free frames

![alt tag](https://cloud.githubusercontent.com/assets/1572847/23592573/e70feef0-01b7-11e7-80f6-ed46a44bdb2f.png)

- PM[s] accesses the ST
    - if the entry is 0 > it points to a resident PT
- PM[PM[s]+p] accesses the PT
    - if the entry is 0 > it points to a resident page
- All ST/PT entries are multiples of 512 (frame size) 
- A bit map is used to keep track of free/occupied frames
- The bit map consists of 1024 bits (one per frame)
- Can be implemented as an array of 32 ints
- Normally this would be mainteined inside the PM but in this projects, it may be implemented as a separate data structure.

## 5. Address Translation Process
- Break each VA into s, p, w
- For read access:
    - If ST or PT entry is -1 then output "pf" (page fault) and contnue with next VA
    - If ST or PT entry is 0 then output "error" and continue with next VA
    - Otherwise output PA = PM[ PM[s] + p ] + w
- For write access:
    - If ST or PT entry is -1 then output "pf"
    - If ST entry is 0 then
         - allocate new blank PT (all zeros)
         - update the ST entry accordingly
         - continue with the translation process
    - If PT entry is 0 then
         - create a new blank page
         - update the PT entry accordingly
         - output the newly generated PA
         - continue with the translation process
    - Otherwise output the corresponding PA: PA = PM[PM[s]+p]+w

## 6. Initialization of PM
- Read init file (in format as below)
    - s_1 f_1 s_2 f_2 ... s_n f_n
    - p_1 s_1 f_1 p_2 s_2 f_2 ... p_m s_m f_m
- s_i f_i: PT of segment s_i starts at address f_i
    - if f_i = -1 then the corresponding PT is not resident
    - ie.
        - 15 512: PT of seg 15 starts at address 512
        - 9 -1: PT of seg 9 is not resident
- p_j s_j f_j: page p_j of segment s_j starts at address f_j
    - if f_i = -1 then the corresponding page is not resident
    - ie.
        - 7 13 4096: page 7 of seg 13 starts at 4096
        - 8 13 -1: page 8 of seg 13 is not resident
- Initialization process:
    - Reads s_i f_i pairs and make corresponding entries in ST's
    - Reads p_j s_j f_j triples and make entries in PT's 
    - Create bitmap to show which frames are free
- Note: each f is a PA, not just a frame number

## 7. Running the VM Translation
- Read input file:
    - o_1 VA_1 o_2 VA_2 ... o_n VA_n
    - each o_i is either 0 (read) or 1 (write)
    - each VA_i is a positive integer (virtual address)
- For each o_i VA_i pair attempts to translate VA into PA
- Write results into an output file

## 8. The Translation Lookside Buffer (TLB) 
![alt tag](https://cloud.githubusercontent.com/assets/1572847/23639403/702a8f62-029c-11e7-8453-4c5d189c6a99.png)

- Size: 4 lines
- LRU (Least Recently Used): int 0:3
- 0: least recently accessed
- 3: most recently accessed
- 0 should be replaced (victim), 3 should not
- s,p: int  
- f: int (starting frame address, not frame #)

## 9. Running Translations with TLB
- Break VA into sp and w
- Search TLB for match on sp
- if TLB hit
    - use f from TLB to form PA = f+w
    - update LRU fields as follow:
        - assume the match is in the line k then:
        - decrement all the LRU values greater than LRU[k] by 1
        - set LRU[k] = 3
- if TLB miss
    - resolve VA as before (breaking VA into sp and w, search TLB for match on sp)
    - in case of error or page fault, no change to TLB
    - if a valid PA is derived then TLB is updated as follows:
        - select line with LRU = 0 and set this LRU = 3
        - replace sp field of that line with the new sp value
        - replace f field of that line with PM[PM[s]+p]
        - decrement all other LRU values by 1

## 10. Bitmap
- Implemented for PM management (keep tracking free/occupied frames)
- BM size : # of bits needed = # of ldisk blocks
- represent BM as an array of int (32 bits each): BM[n]
- How to set, reset, and search for bits in BM?
- prepare a mask array: MASK[32]
    - diagonal contains "1", all other fields are "0"
    - use bit operations (bitwise or/and) to manipulate bits
- MASK (assume 16 bits only; actually 32 bits in implementation)
[alt tag](https://cloud.githubusercontent.com/assets/1572847/23641766/45954e7c-02ab-11e7-89e6-924a8b56f07d.png)
- to Set: bit i of BM[j] to "1":
    - BM[j] = BM[j] | MASK[i]
- How to create MASK[32]
    - MASK[31] = 1
    - MASK[i] = MASK[i+1] <<
- to Set: bit i of BM[j] to "0":
    - create MASK2 where MASK2[i] = ~MASK[i]
    - e.g.,0010 0000 0000 0000 -> 1101 1111 1111 1111
    - BM[j] = BM[j] & MASK2[i]
- to search for a bit equal to "0" in BM:
    - for (i=0;...)  /* search BM from the beginning
        - for (j=0;...)  /* search each bit in BM[i] for "0"
             - test = BM[i] & MASK[j]
             - if (test==0) then
                  - bit j of MB[i] is "0";
                  - stop search

## 11. Summary of Tasks
- Design and implement a VM memory system using segmentation and paging
- Design and implement a TLB to speed up the address translation process
- Design and implement a driver program that initialize the system for a given file.
It then reads another input file and, for each VA, attempts to translate it into corresponding PA.
It outputs the result of each address translation into a new file.
- Submit docs
- Schedule testing
- Follow [the protocol](http://www.ics.uci.edu/~bic/courses/143B/VM-TLB-Project/protocol.pdf)


## - [Virtual Memory Paging Basics Note](http://www.toves.org/books/vm/)
### Intro
- The system stores the official copy of memory on disk and caches only the most frequently used data in RAM.
- To make this workable, we break virtual memory into chunks called pages; a typical page size is four kilobytes.
- We also break RAM into page frames, each the same size as a page, ready to hold any page of virtual memory.
- The system also maintains a page table, stored in RAM, which is an array of entries, one for each page, storing information about the page

![alt tag](https://cloud.githubusercontent.com/assets/1572847/23149627/2cc123bc-f7a2-11e6-87f8-fe8ee69ddc6e.png)

### Example
- The size of one VM is 15 bits long, which 32k bytes.
	- 8 pages / 1 VM * 4k bytes / page = 32k bytes / 1 VM
- the RAM's page table is correspondants of the virtual memory
	- The data of page 0 in VM is stored in the frame 2 in RAM
	- The data of page 2 in VM is stored in the frame 3 in RAM
	- The data of page 4 in VM is stored in the frame 1 in RAM

### Address Translation
- From CPU, it asks utilizing a data referencing VM, not actual RAM PA (Physical Address)
- Since VM does not contain the actual data, we need to translate the VM to PM
- Procedure:
	1. CPU breaks the adress into the first three bits, which represents a particular page (2^3 = 8) and the rest of twelve bits, which represents giving the offset offs within the page.
	2. CPU looks into the page table and try to fetch the corresponding frame
	3. IF page is not in the frame in RAM, it initiates the page fault.
	4. ELSE, CPU loads from the memory address offs within page frame f

### Page Table Format
- A Page Table contains multiple page entries
- Each entry, depending on its design, contains specific bits for each purpose.
	- Load Bit: a bit to represents wthether the page is currently loaded onto memory or not
	- Frame Bits: bits to locate which page frame contains the page.
	- Dirty Bit: a bit specifies whether the page in memory has been altered since being loaded onto memory.
	This is useful to reduce the cost of writing back to disk when the page is removed from the memory.
	This makes sure it wirte back to the disk only if the page is updated since it has been loaded onto memory.
	- Referenced Bit: this is set as 1 whenever the page is accessed.
	OS periodically visits this bit to see whether it's 1 and set it 0.
	IF it's 1, then it indicates the page recently accesessed since preivous prediodic checking mentioned above.
	OTHERWISE, it has not been utilized so it might be good to empty the page from frame to allocate space for another page.

## - [VM Segmentation with Paging Note](http://lass.cs.umass.edu/~shenoy/courses/fall08/lectures/Lec16.pdf)
### Intro
- Segementation of the techniqeu to build a subset of VM addresses to correspond logically with user's system usage
- Component: Segmentation Table: Entries which each entry contains
	- Base Address
	- Length of segment
	- Protection Info
- System generates virtual addressses whose upper order bits are a segment number
- Now the VM space is treated as a collection of segments of arbitraty sizes
	- indicating the segment size differ based on the usage of the segement (global var, stack, heap etc..)
- Physical Memory (PM) is treated as a sequence of fixed size page frames.
- Segments are typicalyl larget than Page Frames

### Addresses in Segmented Paging System
- VM becomes a sequece of bits to represent
	- a segment number (which segement?)
		- this yeilds the base address of the particular page table for that segment
	- a page within the segment (which page in the segment?)
		- can be indexed by the page number of the rest of bits in the VM
	- an offset within the page (which actual PM in the page?)
		- the offset point to the requested physical address finally.

![alt tag](https://cloud.githubusercontent.com/assets/1572847/23151605/220ee990-f7b1-11e6-8c3d-138039818b26.png)

# autonom-car
# autonom-car
