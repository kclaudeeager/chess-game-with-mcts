# 🐳 Chess Engine Docker Deployment

This directory contains everything needed to deploy the Modular Chess Engine using Docker.

## 🚀 Quick Start

### Using the Deployment Script (Recommended)

```bash
# Make script executable (first time only)
chmod +x deploy.sh

# Start the chess engine
./deploy.sh start

# Or start with production setup (includes Nginx)
./deploy.sh production
```

### Manual Docker Commands

```bash
# Build and start
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

## 📋 Prerequisites

- Docker (v20.0+)
- Docker Compose (v2.0+)
- 2GB free disk space
- Port 8000 available (or 80/443 for production)

## 🔧 Deployment Options

### Development Mode
- Direct access to the application on port 8000
- Hot reload enabled
- Development debugging

```bash
./deploy.sh start
# or
docker-compose up -d
```

### Production Mode
- Nginx reverse proxy on port 80
- SSL termination ready
- Rate limiting and security headers
- Optimized for performance

```bash
./deploy.sh production
# or
docker-compose --profile production up -d
```

## 🌐 Access Points

After deployment, the chess engine will be available at:

- **Development**: http://localhost:8000
- **Production**: http://localhost (with Nginx)

### API Endpoints
- Main application: `/`
- API base: `/api/`
- WebSocket: `/ws/{session_id}`
- Health check: `/` (returns 200 OK)

## 📂 File Structure

```
├── Dockerfile              # Main application container
├── docker-compose.yml      # Production Docker Compose
├── docker-compose.dev.yml  # Development overrides
├── requirements.txt        # Python dependencies
├── nginx.conf              # Nginx configuration
├── deploy.sh              # Deployment script
├── .dockerignore          # Docker build exclusions
└── README-Docker.md       # This file
```

## 🎛️ Configuration

### Environment Variables

The application supports these environment variables:

- `ENV`: `development` or `production`
- `DEBUG`: Enable debug mode (`true`/`false`)
- `PYTHONPATH`: Python module path (set to `/app`)

### Persistent Data

- Chess game database: `/app/data/db/`
- RL training data: `/app/data/rl_games/`
- Application logs: `/app/logs/`

Data is persisted using Docker volumes.

## 🔧 Deployment Script Commands

```bash
./deploy.sh build      # Build Docker image
./deploy.sh start      # Start development mode
./deploy.sh production # Start with Nginx (production)
./deploy.sh stop       # Stop all services
./deploy.sh restart    # Restart services
./deploy.sh logs       # View application logs
./deploy.sh status     # Show container status
./deploy.sh test       # Test deployment
./deploy.sh cleanup    # Clean up Docker resources
./deploy.sh help       # Show help
```

## 🏥 Health Monitoring

### Health Checks
- Container health check every 30 seconds
- Endpoint: `curl -f http://localhost:8000/`
- Automatic restart on health check failure

### Monitoring Commands
```bash
# Check container status
docker-compose ps

# View live logs
docker-compose logs -f chess-engine

# Check health status
docker inspect --format='{{.State.Health.Status}}' mcts_chess-engine_1
```

## 🔒 Security Features

### Production Security (with Nginx)
- Rate limiting on API endpoints
- Security headers (XSS, CSRF protection)
- Request size limits
- CORS handling

### SSL/HTTPS Setup
1. Obtain SSL certificates
2. Place them in `./ssl/` directory
3. Uncomment HTTPS server block in `nginx.conf`
4. Update domain name in configuration

## 🐛 Troubleshooting

### Common Issues

**Port already in use:**
```bash
sudo lsof -i :8000  # Find process using port 8000
sudo kill -9 <PID>  # Kill the process
```

**Build failures:**
```bash
./deploy.sh cleanup  # Clean up Docker resources
./deploy.sh build    # Rebuild
```

**Permission issues:**
```bash
sudo chmod +x deploy.sh
sudo chown -R $USER:$USER .
```

### Debug Commands
```bash
# Enter container shell
docker-compose exec chess-engine bash

# View container logs
docker-compose logs chess-engine

# Check resource usage
docker stats

# Inspect container
docker inspect mcts_chess-engine_1
```

## 📊 Performance Tuning

### Resource Limits
Edit `docker-compose.yml` to add resource limits:

```yaml
services:
  chess-engine:
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
        reservations:
          cpus: '0.5'
          memory: 256M
```

### Scaling
For high-traffic deployments:

```bash
# Scale to multiple instances
docker-compose up -d --scale chess-engine=3

# Use external load balancer
# Configure Nginx upstream with multiple backends
```

## 🔄 Updates and Maintenance

### Updating the Application
```bash
# Pull latest code
git pull

# Rebuild and restart
./deploy.sh restart
```

### Database Backup
```bash
# Backup persistent data
docker run --rm -v mcts_chess_data:/data -v $(pwd):/backup alpine tar czf /backup/chess_backup.tar.gz /data
```

### Log Rotation
Logs are automatically rotated by Docker. Configure in Docker daemon:

```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```

## 🌍 Production Deployment

### Cloud Deployment
The Docker setup works on:
- AWS ECS/EC2
- Google Cloud Run/GKE
- Azure Container Instances/AKS
- DigitalOcean Droplets
- Any VPS with Docker support

### DNS and Domain Setup
1. Point your domain to the server IP
2. Update `nginx.conf` with your domain name
3. Configure SSL certificates
4. Enable HTTPS server block

## 📞 Support

If you encounter issues with the Docker deployment:

1. Check the troubleshooting section above
2. View logs: `./deploy.sh logs`
3. Test deployment: `./deploy.sh test`
4. Clean and rebuild: `./deploy.sh cleanup && ./deploy.sh build`

The chess engine includes comprehensive logging and error handling to help diagnose issues quickly.
