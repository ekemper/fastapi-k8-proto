#!/bin/bash

# Script to find and kill PostgreSQL and Redis processes on macOS
# Also checks for and disables startup services (Homebrew services, LaunchAgents, LaunchDaemons)
# Usage: ./scripts/kill-db-processes.sh [--force]
#
# Options:
#   --force    Skip confirmation prompts and force kill/disable everything

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if force flag is provided
FORCE_KILL=false
if [[ "$1" == "--force" ]]; then
    FORCE_KILL=true
fi

echo -e "${BLUE}🔍 Searching for PostgreSQL and Redis processes...${NC}"

# Function to find and display processes
find_processes() {
    local service_name=$1
    local process_patterns=("${@:2}")
    
    echo -e "\n${YELLOW}--- $service_name Processes ---${NC}"
    
    local found_processes=()
    for pattern in "${process_patterns[@]}"; do
        while IFS= read -r line; do
            if [[ -n "$line" ]]; then
                found_processes+=("$line")
            fi
        done < <(pgrep -fl "$pattern" 2>/dev/null || true)
    done
    
    if [[ ${#found_processes[@]} -eq 0 ]]; then
        echo -e "${GREEN}✅ No $service_name processes found${NC}"
        return 1
    else
        echo -e "${RED}Found ${#found_processes[@]} $service_name process(es):${NC}"
        for process in "${found_processes[@]}"; do
            echo "  PID: $process"
        done
        return 0
    fi
}

# Function to kill processes
kill_processes() {
    local service_name=$1
    local process_patterns=("${@:2}")
    
    local pids=()
    for pattern in "${process_patterns[@]}"; do
        while IFS= read -r pid; do
            if [[ -n "$pid" ]]; then
                pids+=("$pid")
            fi
        done < <(pgrep "$pattern" 2>/dev/null || true)
    done
    
    if [[ ${#pids[@]} -eq 0 ]]; then
        return 0
    fi
    
    if [[ "$FORCE_KILL" == "false" ]]; then
        echo -e "\n${YELLOW}Do you want to kill these $service_name processes? (y/N):${NC}"
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            echo -e "${BLUE}Skipping $service_name processes${NC}"
            return 0
        fi
    fi
    
    echo -e "${BLUE}Killing $service_name processes...${NC}"
    
    # Try graceful shutdown first (SIGTERM)
    for pid in "${pids[@]}"; do
        if kill -TERM "$pid" 2>/dev/null; then
            echo -e "${GREEN}✅ Sent SIGTERM to PID $pid${NC}"
        fi
    done
    
    # Wait a moment for graceful shutdown
    sleep 2
    
    # Force kill any remaining processes (SIGKILL)
    for pid in "${pids[@]}"; do
        if kill -0 "$pid" 2>/dev/null; then
            if kill -KILL "$pid" 2>/dev/null; then
                echo -e "${RED}💀 Force killed PID $pid${NC}"
            fi
        fi
    done
}

# PostgreSQL process patterns
POSTGRES_PATTERNS=(
    "postgres"
    "postmaster"
    "pg_ctl"
)

# Redis process patterns  
REDIS_PATTERNS=(
    "redis-server"
    "redis-cli"
    "redis-sentinel"
)

# Find PostgreSQL processes
if find_processes "PostgreSQL" "${POSTGRES_PATTERNS[@]}"; then
    POSTGRES_FOUND=true
else
    POSTGRES_FOUND=false
fi

# Find Redis processes
if find_processes "Redis" "${REDIS_PATTERNS[@]}"; then
    REDIS_FOUND=true
else
    REDIS_FOUND=false
fi

# If no processes found, exit
if [[ "$POSTGRES_FOUND" == "false" && "$REDIS_FOUND" == "false" ]]; then
    echo -e "\n${GREEN}🎉 No PostgreSQL or Redis processes found running${NC}"
    exit 0
fi

echo -e "\n${BLUE}===========================================${NC}"

# Kill processes if found
if [[ "$POSTGRES_FOUND" == "true" ]]; then
    kill_processes "PostgreSQL" "${POSTGRES_PATTERNS[@]}"
fi

if [[ "$REDIS_FOUND" == "true" ]]; then
    kill_processes "Redis" "${REDIS_PATTERNS[@]}"
fi

echo -e "\n${GREEN}🎉 Process cleanup completed${NC}"

# Function to check and disable startup services
disable_startup_services() {
    echo -e "\n${BLUE}🔍 Checking for startup services...${NC}"
    
    local services_found=false
    
    # Check for Homebrew services
    if command -v brew >/dev/null 2>&1; then
        echo -e "\n${YELLOW}--- Homebrew Services ---${NC}"
        
        # PostgreSQL services
        local postgres_services=(
            "postgresql"
            "postgresql@14"
            "postgresql@15"
            "postgresql@16"
            "postgres"
        )
        
        # Redis services
        local redis_services=(
            "redis"
        )
        
        local running_services=()
        
        # Check PostgreSQL services
        for service in "${postgres_services[@]}"; do
            if brew services list | grep -q "^$service.*started"; then
                running_services+=("$service (PostgreSQL)")
                services_found=true
            fi
        done
        
        # Check Redis services
        for service in "${redis_services[@]}"; do
            if brew services list | grep -q "^$service.*started"; then
                running_services+=("$service (Redis)")
                services_found=true
            fi
        done
        
        if [[ ${#running_services[@]} -gt 0 ]]; then
            echo -e "${RED}Found ${#running_services[@]} running Homebrew service(s):${NC}"
            for service in "${running_services[@]}"; do
                echo "  - $service"
            done
            
            if [[ "$FORCE_KILL" == "false" ]]; then
                echo -e "\n${YELLOW}Do you want to stop and disable these Homebrew services? (y/N):${NC}"
                read -r response
                if [[ "$response" =~ ^[Yy]$ ]]; then
                    for service in "${postgres_services[@]}" "${redis_services[@]}"; do
                        if brew services list | grep -q "^$service.*started"; then
                            echo -e "${BLUE}Stopping and disabling $service...${NC}"
                            brew services stop "$service" 2>/dev/null || true
                        fi
                    done
                    echo -e "${GREEN}✅ Homebrew services disabled${NC}"
                fi
            else
                for service in "${postgres_services[@]}" "${redis_services[@]}"; do
                    if brew services list | grep -q "^$service.*started"; then
                        echo -e "${BLUE}Stopping and disabling $service...${NC}"
                        brew services stop "$service" 2>/dev/null || true
                    fi
                done
                echo -e "${GREEN}✅ Homebrew services disabled${NC}"
            fi
        else
            echo -e "${GREEN}✅ No running Homebrew services found${NC}"
        fi
    else
        echo -e "${YELLOW}Homebrew not found, skipping Homebrew services check${NC}"
    fi
    
    # Check for LaunchAgents and LaunchDaemons
    echo -e "\n${YELLOW}--- Launch Services ---${NC}"
    
    local launch_dirs=(
        "/Library/LaunchDaemons"
        "/Library/LaunchAgents"
        "$HOME/Library/LaunchAgents"
    )
    
    local launch_patterns=(
        "*postgres*"
        "*postgresql*"
        "*redis*"
    )
    
    local found_launch_services=()
    
    for dir in "${launch_dirs[@]}"; do
        if [[ -d "$dir" ]]; then
            for pattern in "${launch_patterns[@]}"; do
                while IFS= read -r -d '' file; do
                    if [[ -f "$file" ]]; then
                        found_launch_services+=("$file")
                    fi
                done < <(find "$dir" -name "$pattern" -print0 2>/dev/null || true)
            done
        fi
    done
    
    if [[ ${#found_launch_services[@]} -gt 0 ]]; then
        echo -e "${RED}Found ${#found_launch_services[@]} launch service(s):${NC}"
        for service in "${found_launch_services[@]}"; do
            echo "  - $(basename "$service")"
            # Check if service is loaded
            local service_name=$(basename "$service" .plist)
            if launchctl list | grep -q "$service_name" 2>/dev/null; then
                echo "    ${RED}(currently loaded)${NC}"
            else
                echo "    ${GREEN}(not loaded)${NC}"
            fi
        done
        
        if [[ "$FORCE_KILL" == "false" ]]; then
            echo -e "\n${YELLOW}Do you want to unload these launch services? (y/N):${NC}"
            read -r response
            if [[ "$response" =~ ^[Yy]$ ]]; then
                for service in "${found_launch_services[@]}"; do
                    local service_name=$(basename "$service" .plist)
                    echo -e "${BLUE}Unloading $service_name...${NC}"
                    launchctl unload "$service" 2>/dev/null || true
                done
                echo -e "${GREEN}✅ Launch services unloaded${NC}"
            fi
        else
            for service in "${found_launch_services[@]}"; do
                local service_name=$(basename "$service" .plist)
                echo -e "${BLUE}Unloading $service_name...${NC}"
                launchctl unload "$service" 2>/dev/null || true
            done
            echo -e "${GREEN}✅ Launch services unloaded${NC}"
        fi
        services_found=true
    else
        echo -e "${GREEN}✅ No launch services found${NC}"
    fi
    
    if [[ "$services_found" == "false" ]]; then
        echo -e "${GREEN}✅ No startup services found${NC}"
    fi
}

# Disable startup services
disable_startup_services

# Verify cleanup
echo -e "\n${BLUE}Verifying process cleanup...${NC}"
sleep 1

REMAINING_POSTGRES=$(pgrep -f "postgres|postmaster|pg_ctl" 2>/dev/null | wc -l | tr -d ' ')
REMAINING_REDIS=$(pgrep -f "redis" 2>/dev/null | wc -l | tr -d ' ')

if [[ "$REMAINING_POSTGRES" -eq 0 && "$REMAINING_REDIS" -eq 0 ]]; then
    echo -e "${GREEN}✅ All processes successfully terminated${NC}"
else
    echo -e "${YELLOW}⚠️  Some processes may still be running:${NC}"
    [[ "$REMAINING_POSTGRES" -gt 0 ]] && echo -e "  PostgreSQL: $REMAINING_POSTGRES processes"
    [[ "$REMAINING_REDIS" -gt 0 ]] && echo -e "  Redis: $REMAINING_REDIS processes"
fi 