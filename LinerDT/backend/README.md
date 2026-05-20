# LinerDT Backend

## Setup

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## API Endpoints

- `GET /api/health` - Health check
- `GET /api/sim/state` - Get simulation state
- `POST /api/sim/start` - Start simulation
- `POST /api/sim/pause` - Pause simulation
- `POST /api/sim/set-speed` - Set simulation speed
- `POST /api/sim/jump-to` - Jump to time
- `POST /api/sim/reset` - Reset simulation
- `WS /ws/sim` - WebSocket endpoint
