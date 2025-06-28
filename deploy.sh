#!/bin/bash

# Chess Engine Deployment Script
# This script helps deploy the chess engine using Docker

set -e

echo "🚀 Chess Engine Deployment Script"
echo "================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is installed
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        echo "Visit: https://docs.docker.com/get-docker/"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        echo "Visit: https://docs.docker.com/compose/install/"
        exit 1
    fi
    
    print_success "Docker and Docker Compose are installed"
}

# Build the application
build_app() {
    print_status "Building Chess Engine Docker image..."
    docker-compose build chess-engine
    print_success "Build completed"
}

# Start the application
start_app() {
    print_status "Starting Chess Engine..."
    docker-compose up -d chess-engine
    print_success "Chess Engine started"
    
    # Wait for the application to be ready
    print_status "Waiting for application to be ready..."
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f http://localhost:8000/ &> /dev/null; then
            print_success "Application is ready!"
            break
        fi
        
        if [ $attempt -eq $max_attempts ]; then
            print_error "Application failed to start after $max_attempts attempts"
            print_status "Checking logs..."
            docker-compose logs chess-engine
            exit 1
        fi
        
        echo -n "."
        sleep 2
        ((attempt++))
    done
}

# Start with production setup (nginx)
start_production() {
    print_status "Starting Chess Engine with Nginx (Production mode)..."
    docker-compose --profile production up -d
    print_success "Production setup started"
    
    print_status "Waiting for services to be ready..."
    sleep 10
    
    if curl -f http://localhost/ &> /dev/null; then
        print_success "Production setup is ready!"
        print_status "Application is available at: http://localhost/"
    else
        print_error "Production setup failed to start"
        docker-compose logs
        exit 1
    fi
}

# Stop the application
stop_app() {
    print_status "Stopping Chess Engine..."
    docker-compose down
    print_success "Chess Engine stopped"
}

# Show logs
show_logs() {
    print_status "Showing Chess Engine logs..."
    docker-compose logs -f chess-engine
}

# Show status
show_status() {
    print_status "Chess Engine Status:"
    docker-compose ps
    
    echo ""
    print_status "Container logs (last 20 lines):"
    docker-compose logs --tail=20 chess-engine
}

# Clean up
cleanup() {
    print_status "Cleaning up Docker images and containers..."
    docker-compose down -v --remove-orphans
    docker system prune -f
    print_success "Cleanup completed"
}

# Test the deployment
test_deployment() {
    print_status "Testing deployment..."
    
    # Test main page
    if curl -f http://localhost:8000/ &> /dev/null; then
        print_success "✓ Main page accessible"
    else
        print_error "✗ Main page not accessible"
        return 1
    fi
    
    # Test API endpoint
    if curl -f http://localhost:8000/api/session -X POST -H "Content-Type: application/json" -d '{"game_mode": "human_vs_ai"}' &> /dev/null; then
        print_success "✓ API endpoints working"
    else
        print_error "✗ API endpoints not working"
        return 1
    fi
    
    print_success "All tests passed!"
}

# Show help
show_help() {
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  build      Build the Docker image"
    echo "  start      Start the Chess Engine (development mode)"
    echo "  production Start with Nginx reverse proxy (production mode)"
    echo "  stop       Stop the Chess Engine"
    echo "  restart    Restart the Chess Engine"
    echo "  logs       Show application logs"
    echo "  status     Show container status and recent logs"
    echo "  test       Test the deployment"
    echo "  cleanup    Clean up Docker images and containers"
    echo "  help       Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 start                    # Start in development mode"
    echo "  $0 production              # Start with nginx (production)"
    echo "  $0 logs                    # View logs"
    echo "  $0 test                    # Test if everything works"
}

# Main script logic
case "${1:-help}" in
    "build")
        check_docker
        build_app
        ;;
    "start")
        check_docker
        build_app
        start_app
        print_success "🎉 Chess Engine is running at http://localhost:8000"
        print_status "To view logs: $0 logs"
        print_status "To stop: $0 stop"
        ;;
    "production")
        check_docker
        build_app
        start_production
        print_success "🎉 Chess Engine is running at http://localhost (with Nginx)"
        print_status "To view logs: $0 logs"
        print_status "To stop: $0 stop"
        ;;
    "stop")
        stop_app
        ;;
    "restart")
        check_docker
        stop_app
        build_app
        start_app
        print_success "🎉 Chess Engine restarted"
        ;;
    "logs")
        show_logs
        ;;
    "status")
        show_status
        ;;
    "test")
        test_deployment
        ;;
    "cleanup")
        cleanup
        ;;
    "help"|*)
        show_help
        ;;
esac
