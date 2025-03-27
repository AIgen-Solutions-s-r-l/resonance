# Redis Caching Architecture

## Overview

The Redis caching solution provides a distributed caching mechanism for the job matching service, replacing the previous in-memory cache with a more robust, scalable solution that works across multiple service replicas.

## Architecture Diagram

```mermaid
graph TD
    A[Application] --> B[HybridCache]
    B --> C1[Redis Cache Client]
    B -.-> C2[In-Memory Cache]
    C1 --> D[Redis Connection Manager]
    D --> E[Redis Server]
    D -.-> F[Error Handler]
    F --> G[Circuit Breaker]
    G --> H[Backoff/Retry]
    
    classDef primary fill:#d1eaff,stroke:#0066cc
    classDef secondary fill:#ffe6cc,stroke:#ff9933
    classDef middleware fill:#e6ffcc,stroke:#66cc00
    
    class A,B primary
    class C1,D,E secondary
    class F,G,H,C2 middleware
```

## Component Descriptions

### HybridCache
The main cache interface that applications interact with. It automatically routes cache operations to Redis when available, with fallback to in-memory cache when Redis is unavailable.

- **Purpose**: Provide a unified caching interface with fallback mechanisms
- **Responsibilities**:
  - Route cache operations to Redis
  - Fall back to in-memory cache when Redis is unavailable
  - Handle initialization of both cache systems
  - Provide the same API as the original cache

### Redis Cache Client
Handles Redis-specific cache operations including serialization, key management, and TTL handling.

- **Purpose**: Provide Redis-specific caching implementation
- **Responsibilities**:
  - Serialize/deserialize data for Redis storage
  - Manage TTL for cache entries
  - Handle Redis errors with backoff and retry
  - Maintain compatibility with existing cache interface

### Redis Connection Manager
Manages connections to the Redis server with connection pooling and health checking.

- **Purpose**: Manage Redis connections efficiently
- **Responsibilities**:
  - Create and maintain a connection pool
  - Perform periodic health checks
  - Handle connection errors
  - Implement reconnection logic
  - Manage connection lifecycle

### Circuit Breaker
Prevents cascade failures when Redis is unavailable by temporarily stopping Redis operation attempts.

- **Purpose**: Protect the application from Redis failures
- **Responsibilities**:
  - Track connection failures
  - Open circuit (block operations) after failure threshold
  - Automatically attempt recovery after timeout
  - Provide half-open state for testing recovery

### In-Memory Cache
The original in-memory cache implementation, maintained for backward compatibility and fallback.

- **Purpose**: Provide local fallback when Redis is unavailable
- **Responsibilities**:
  - Store cache entries locally
  - Manage TTL and cleanup
  - Maintain the original cache interface

## Sequence Diagrams

### Cache Get Operation

```mermaid
sequenceDiagram
    participant App as Application
    participant HC as HybridCache
    participant RC as Redis Cache
    participant CM as Connection Manager
    participant CB as Circuit Breaker
    participant Redis as Redis Server
    participant IMC as In-Memory Cache
    
    App->>HC: get(key)
    
    alt Redis Available
        HC->>RC: get(key)
        RC->>CM: get_redis()
        CM->>CB: is_allowed()
        
        alt Circuit Closed
            CB-->>CM: true
            CM->>Redis: get(key)
            Redis-->>CM: value or null
            CM-->>RC: value or null
            RC-->>HC: deserialized value or null
        else Circuit Open
            CB-->>CM: false
            CM-->>RC: RedisCircuitBreakerOpenError
            RC-->>HC: null
        end
    else Redis Error
        HC->>IMC: get(key)
        IMC-->>HC: value or null
    end
    
    HC-->>App: value or null
```

### Cache Set Operation

```mermaid
sequenceDiagram
    participant App as Application
    participant HC as HybridCache
    participant RC as Redis Cache
    participant CM as Connection Manager
    participant CB as Circuit Breaker
    participant Redis as Redis Server
    participant IMC as In-Memory Cache
    
    App->>HC: set(key, value)
    
    par Redis Cache
        HC->>RC: set(key, value)
        RC->>CM: get_redis()
        CM->>CB: is_allowed()
        
        alt Circuit Closed
            CB-->>CM: true
            CM->>Redis: setex(key, ttl, serialized_value)
            Redis-->>CM: ok
            CM-->>RC: true
            RC-->>HC: true
        else Circuit Open
            CB-->>CM: false
            CM-->>RC: RedisCircuitBreakerOpenError
            RC-->>HC: false
        end
    and In-Memory Cache
        HC->>IMC: set(key, value)
        IMC-->>HC: true
    end
    
    HC-->>App: true
```

## Error Handling Flow

```mermaid
flowchart TD
    A[Redis Operation] --> B{Circuit Open?}
    B -- Yes --> C[Skip Operation]
    B -- No --> D[Attempt Operation]
    D --> E{Success?}
    E -- Yes --> F[Record Success]
    F --> G[Reset Failure Count]
    G --> H[Close Circuit if Half-Open]
    E -- No --> I[Record Failure]
    I --> J[Increment Failure Count]
    J --> K{Retry Count < Max?}
    K -- Yes --> L[Wait with Backoff]
    L --> D
    K -- No --> M[Fallback to Memory Cache]
    J --> N{Threshold Reached?}
    N -- Yes --> O[Open Circuit]
    N -- No --> K
```

## Deployment Considerations

- **Redis Configuration**: Redis server should be configured for high availability
- **Connection Pooling**: Pool size should be adjusted based on instance count and expected load
- **TTL Strategy**: Cache TTL should be configured based on data volatility
- **Memory Monitoring**: Redis memory usage should be monitored to prevent OOM conditions
- **Network Latency**: Redis server should be in the same region as the application to minimize latency