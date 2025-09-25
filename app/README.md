# Alert Management Multi-Agent System

A sophisticated multi-agent orchestrator system designed to intelligently process and suppress noisy alerts while maintaining visibility of critical issues.

## Overview

This system uses multiple specialized AI agents working together to:
- Analyze incoming alerts for patterns and noise
- Detect duplicate alerts within configurable time windows
- Use machine learning models to predict alert suppression likelihood
- Apply business rules to make final suppression decisions
- Maintain comprehensive audit trails of all decisions

## Architecture

### Multi-Agent Components

1. **Alert Management Orchestrator (Root Agent)**
   - Coordinates the entire alert processing workflow
   - Routes tasks to appropriate specialized agents
   - Makes final decisions based on agent recommendations

2. **Alert Agent**
   - Performs initial alert analysis and characterization
   - Checks for duplicate alerts within time windows
   - Manages alert suppression and forwarding actions
   - Maintains alert history and patterns

3. **Data Agent**
   - Executes SQL queries to retrieve alert history
   - Provides data context for ML predictions
   - Supports duplicate detection with historical data
   - Manages BigQuery operations

4. **ML Agent**
   - Predicts alert suppression using trained ML models
   - Provides confidence scores and explanations
   - Applies business rules for final decisions
   - Analyzes alert patterns for classification

## Key Features

### Intelligent Alert Suppression
- **ML-Based Predictions**: Uses trained models to predict which alerts should be suppressed
- **Confidence Thresholds**: Configurable confidence levels for suppression decisions
- **Business Rules**: Never suppress critical alerts (severity-1 or Sev1), always maintain operational visibility
- **Decision Tracking**: Tracks decisions with 'keep' or 'suppressed: jira exists' values

### Duplicate Detection
- **Time-Window Based**: Configurable duplicate detection windows (default: 5 minutes)
- **Multi-Factor Matching**: Matches on host, title, and severity
- **Historical Analysis**: Considers alert patterns over time

### Comprehensive Logging
- **Audit Trail**: Complete record of all alert processing decisions
- **Reasoning**: Clear explanations for suppression/forwarding decisions
- **Performance Metrics**: Tracking of suppression rates and system performance

## Configuration

### Environment Variables
```bash
# Model Configuration
ROOT_AGENT_MODEL=gemini-2.0-flash-exp
ALERT_AGENT_MODEL=gemini-2.0-flash-exp
DATA_AGENT_MODEL=gemini-2.0-flash-exp
ML_AGENT_MODEL=gemini-2.0-flash-exp

# BigQuery Configuration
BQ_PROJECT_ID=ruckusoperations
BQ_DATASET_ID=BDC_6
ALERT_CLASSIFIER_MODEL=ruckusoperations.BDC_6.alert_classifier

# Alert Settings
SUPPRESSION_THRESHOLD=0.8
DUPLICATE_WINDOW_MINUTES=5
CRITICAL_ALWAYS_FORWARD=true
```

### Alert Settings
The system supports configurable alert processing parameters:
- `suppression_threshold`: ML confidence threshold for suppression (default: 0.8)
- `duplicate_window_minutes`: Time window for duplicate detection (default: 5)
- `critical_always_forward`: Never suppress critical alerts (default: true)

## Usage

### Processing Alerts
```python
from app.agent_root import root_agent

# Alert data structure
alert_data = {
    "alert_id": "alert_001",
    "host": "web-server-01",
    "severity": "warning",
    "title": "High CPU Usage",
    "description": "CPU usage is above 80%",
    "category": "performance",
    "source": "monitoring_system",
    "timestamp": "2025-01-27T10:30:00Z"
}

# Process through the multi-agent system
result = await root_agent.run_async(
    args={"request": f"Process this alert: {json.dumps(alert_data)}"}
)
```

### Workflow Steps
1. **Initial Analysis**: Alert Agent analyzes the incoming alert
2. **Duplicate Check**: Check for recent similar alerts
3. **ML Prediction**: Use ML model to predict suppression likelihood
4. **Final Decision**: Apply business rules and make final decision
5. **Action Execution**: Suppress or forward the alert with logging

## Database Schema

### Alerts Table
```sql
CREATE TABLE `project.dataset.alerts_data` (
  alert_id STRING,
  host STRING,
  severity STRING,  -- Values: severity-1, severity-2, severity-3, Sev1, Sev2, Sev3
  title STRING,
  description STRING,
  status STRING,
  source STRING,
  timestamp TIMESTAMP,
  decision_reason STRING,  -- Values: 'keep' or 'suppressed: jira exists'
  ml_confidence FLOAT64
);
```

## Examples

See `app/examples/alert_processing_example.py` for a complete demonstration of the system processing various types of alerts.

## Integration

### ADK Web UI
The system is designed to work seamlessly with the Google ADK Web UI:
- All agents use proper ADK Agent structure
- Tools are wrapped as AgentTool instances
- State management through CallbackContext
- Proper error handling and logging

### Notification Systems
The system can be integrated with various notification channels:
- Slack webhooks
- Email notifications
- PagerDuty integration
- Custom webhook endpoints

## Monitoring and Metrics

### Key Metrics
- Alert processing volume
- Suppression rates by severity/category
- ML model accuracy
- System response times
- False positive/negative rates

### Logging
All decisions are logged with:
- Timestamp and alert details
- Decision made (suppress/forward)
- Reasoning and confidence scores
- ML prediction details
- Business rule applications

## Development

### Adding New Agents
1. Create agent directory in `app/agents/`
2. Implement agent.py with proper ADK Agent structure
3. Create tools.py with AgentTool wrappers
4. Add prompts.py with agent instructions
5. Update root agent imports and sub_agents list

### Extending Functionality
- Add new ML models for different alert types
- Implement additional business rules
- Create custom notification channels
- Add new data sources and integrations

## Troubleshooting

### Common Issues
1. **BigQuery Connection**: Ensure proper authentication and project access
2. **ML Model Access**: Verify model exists and is accessible
3. **Agent Routing**: Check agent imports and tool configurations
4. **State Management**: Ensure proper CallbackContext usage

### Debug Mode
Enable debug logging by setting environment variables:
```bash
DEBUG=true
LOG_LEVEL=DEBUG
```

## Contributing

1. Follow the existing code structure and patterns
2. Add comprehensive error handling
3. Include unit tests for new functionality
4. Update documentation for new features
5. Ensure ADK compatibility

## License

This project is licensed under the Apache License 2.0 - see the LICENSE file for details.
