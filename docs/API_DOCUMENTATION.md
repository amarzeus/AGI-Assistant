# AGI Assistant - API Documentation

## Core Services

### FeedbackLoopManager

Manages workflow learning and improvement.

```python
class FeedbackLoopManager:
    async def analyze_execution(
        execution: WorkflowExecution,
        verification_results: List[VerificationResult]
    ) -> FeedbackAnalysis
    
    async def update_confidence(
        workflow_id: str,
        success: bool
    ) -> float
    
    async def suggest_improvements(
        workflow_id: str
    ) -> List[str]
    
    async def adjust_workflow(
        workflow_id: str,
        workflow_data: Dict[str, Any],
        analysis: FeedbackAnalysis
    ) -> Dict[str, Any]
```

### WorkflowParameterizer

Enables workflow reuse with different data.

```python
class WorkflowParameterizer:
    async def identify_parameters(
        workflow: Dict[str, Any]
    ) -> List[Parameter]
    
    async def create_parameter_schema(
        workflow_id: str,
        parameters: List[Parameter]
    ) -> ParameterSchema
    
    async def substitute_parameters(
        workflow: Dict[str, Any],
        values: Dict[str, Any]
    ) -> Dict[str, Any]
    
    async def validate_parameters(
        schema: ParameterSchema,
        values: Dict[str, Any]
    ) -> List[str]
```

### AutomationScheduler

Schedules recurring workflow executions.

```python
class AutomationScheduler:
    async def create_schedule(
        workflow_id: str,
        schedule_config: Dict[str, Any]
    ) -> str
    
    async def get_next_run_time(
        schedule: Schedule
    ) -> datetime
```

### PerformanceMonitor

Monitors application performance.

```python
class PerformanceMonitor:
    def record_metric(name: str, value: float) -> None
    def get_metrics() -> Dict[str, Any]
    def check_thresholds() -> List[str]
```

## Data Models

### Parameter

```python
@dataclass
class Parameter:
    name: str
    type: str  # text, number, date, file, choice
    description: str
    default_value: Optional[Any]
    required: bool
    validation_rules: Dict[str, Any]
```

### Schedule

```python
@dataclass
class Schedule:
    id: str
    workflow_id: str
    schedule_type: ScheduleType
    schedule_config: Dict[str, Any]
    enabled: bool
    last_run: Optional[datetime]
    next_run: Optional[datetime]
    retry_policy: RetryPolicy
```

### FeedbackAnalysis

```python
@dataclass
class FeedbackAnalysis:
    execution_id: str
    workflow_id: str
    overall_success: bool
    confidence: float
    issues_detected: List[str]
    suggested_adjustments: List[Adjustment]
    should_retry: bool
    retry_delay: int
```

## Events

### Event Types

```python
class EventType(Enum):
    WORKFLOW_EXECUTION_STARTED = "workflow_execution_started"
    WORKFLOW_EXECUTION_COMPLETED = "workflow_execution_completed"
    WORKFLOW_EXECUTION_FAILED = "workflow_execution_failed"
    WORKFLOW_EXECUTION_PROGRESS = "workflow_execution_progress"
```

### Event Structure

```python
@dataclass
class Event:
    type: EventType
    timestamp: datetime
    source: str
    data: Dict[str, Any]
```

## Usage Examples

### Execute Workflow with Parameters

```python
# Get parameterizer
parameterizer = WorkflowParameterizer()

# Identify parameters
params = await parameterizer.identify_parameters(workflow)

# Create schema
schema = await parameterizer.create_parameter_schema(
    workflow_id,
    params
)

# Get user values
values = {
    'email': 'user@example.com',
    'count': 5
}

# Validate
errors = await parameterizer.validate_parameters(schema, values)
if errors:
    print(f"Validation errors: {errors}")
    return

# Substitute
workflow_with_params = await parameterizer.substitute_parameters(
    workflow,
    values
)

# Execute
await executor.queue_execution(workflow_with_params)
```

### Create Schedule

```python
scheduler = AutomationScheduler()

schedule_config = {
    'type': 'daily',
    'hour': 9,
    'minute': 0
}

schedule_id = await scheduler.create_schedule(
    workflow_id='workflow_001',
    schedule_config=schedule_config
)
```

### Monitor Performance

```python
monitor = PerformanceMonitor()

# Get current metrics
metrics = monitor.get_metrics()
print(f"CPU: {metrics['cpu_percent']}%")
print(f"Memory: {metrics['memory_mb']}MB")

# Check thresholds
warnings = monitor.check_thresholds()
for warning in warnings:
    print(f"Warning: {warning}")
```

---

For implementation details, see source code in `src/services/`
