flowchart TD
    subgraph "Main PCB"
        Power_In["J2 Barrel 5V"] --> F1["F1 PTC Fuse"] --> REG1["REG1 LDO 3.3V"]
        REG1 --> REG2["REG2 LDO 1.8V"]
        REG1 --> REG3["REG3 LDO 1.0V"]
        REG1 --> REG4["REG4 LDO 5V for RF Amp"]
        REG1 --> LED1["LED1 Power LED + R70"]
        REG1 --> U1["U1 FPGA XC7A35T"]
        REG2 --> U1
        REG3 --> U1
        Y1["Y1 100MHz TCXO"] --> U1
        U1 -->|SPI| U3["U3 ADF4351 PLL Synth"]
        REG1 --> U3
        U3 -->|"Loop Filter R67,R68,C31-C33"| U3
        U3 -->|"RF Out"| U5["U5 HMC441 RF Amp + R69,L2"]
        REG4 --> U5
        U5 -->|"SMA 50Ω"| J3["J3 RF Output to Antenna"]
        J3 --> A1["A1 Microwave Antenna/CPW"]
        U1 -->|"SCCB/I2C + R65,R66"| U2["U2 OV7670 Camera + L1 Lens + F2 Filter"]
        REG1 --> U2
        U1 -->|"UART"| J1["J1 USB-UART"]
        U1 -->|"GPIO Control + R1-R64"| J4["J4 PinHeader to VCSEL PCB"]
        C1C20["Decoupling Caps C1-C20"] -->|"Near all ICs"| GND
        C21C30["Bulk Caps C21-C30"] -->|"Distributed"| GND
        D1D10["ESD Diodes D1-D10"] -->|"On I/O lines"| GND
    end

    subgraph "VCSEL Array PCB"
        J4 --> U4["U4 8x8 VCSEL Array ~532nm"]
        %% Power is supplied to VCSEL PCB via header from REG1 3.3V
        REG1 --> U4
    end

    subgraph "Optical/Quantum Setup"
        U4 -->|"Laser Beams"| hBN["PMMA/hBN Substrate with 64 sites"]
        hBN -->|"Microwave Field"| A1
        hBN -->|"Fluorescence 500-700nm"| U2
    end

    Power_In -.->|"Optional"| J1
    Y2["Y2 24MHz Optional"] -.-> U2
