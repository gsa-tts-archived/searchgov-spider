# Architecture

A basic representation of our architecture is below.  Here you can see a JSON configuration file feeding into a scheduler process which, in turn, launces multiple scrapy processes, each capable of writing to its own target system. The number of concurrent jobs is configurable within the system.
```mermaid
flowchart LR
    J[json config file] --> S[Scheduler]
    S --> P0[Scrapy Process 0] --> T0[Output Target 0]
    S --> P1[Scrapy Process 1] --> T1[Output Target 1]
    S --> P2[Scrapy Process 2] --> T2[Output Target 2]
    S -.-> PN[Scrapy Process N] -.-> TN[Output Target N]
    style PN stroke-dasharray: 5 5
    style TN stroke-dasharray: 5 5
```

The [Scrapy documentation](https://docs.scrapy.org/en/latest/topics/architecture.html) does a good job of explaning the internals of Scrapy, which for us, is encapsulated in each of the "Scrapy Process" blocks above.
