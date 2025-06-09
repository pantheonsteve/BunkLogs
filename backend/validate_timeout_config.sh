#!/bin/bash
# validate_timeout_config.sh - Validate Elastic Beanstalk timeout configuration

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔍 Validating Elastic Beanstalk Timeout Configuration${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"

# Check if we're in the right directory
if [ ! -d ".ebextensions" ]; then
    echo -e "${RED}❌ .ebextensions directory not found${NC}"
    echo -e "${YELLOW}   Please run this script from the backend directory${NC}"
    exit 1
fi

echo -e "${GREEN}✅ .ebextensions directory found${NC}"

# Check timeout configuration files
config_files=(
    "00_timeout.config"
    "01_django.config"
)

echo -e "\n${BLUE}📋 Checking timeout configuration files:${NC}"

for config_file in "${config_files[@]}"; do
    if [ -f ".ebextensions/$config_file" ]; then
        echo -e "${GREEN}✅ $config_file exists${NC}"
        
        # Check for timeout settings
        if grep -q "Timeout:" ".ebextensions/$config_file"; then
            timeout_value=$(grep "Timeout:" ".ebextensions/$config_file" | awk '{print $2}' | head -1)
            echo -e "   • Timeout setting: ${timeout_value} seconds ($((timeout_value / 60)) minutes)"
        fi
    else
        echo -e "${RED}❌ $config_file missing${NC}"
    fi
done

# Validate timeout configuration content
echo -e "\n${BLUE}🔧 Validating timeout configuration:${NC}"

if [ -f ".ebextensions/00_timeout.config" ]; then
    echo -e "${GREEN}✅ Main timeout configuration active${NC}"
    
    # Check specific settings
    if grep -q "Timeout: 1200" ".ebextensions/00_timeout.config"; then
        echo -e "${GREEN}✅ Extended 20-minute timeout configured${NC}"
    else
        echo -e "${YELLOW}⚠️  Warning: 20-minute timeout not found${NC}"
    fi
    
    if grep -q "DockerDaemonTimeout:" ".ebextensions/00_timeout.config"; then
        echo -e "${GREEN}✅ Docker daemon timeout configured${NC}"
    fi
    
    if grep -q "DeploymentPolicy: Rolling" ".ebextensions/00_timeout.config"; then
        echo -e "${GREEN}✅ Rolling deployment policy active${NC}"
    fi
    
    if grep -q "SystemType: enhanced" ".ebextensions/00_timeout.config"; then
        echo -e "${GREEN}✅ Enhanced health reporting enabled${NC}"
    fi
else
    echo -e "${RED}❌ Main timeout configuration missing${NC}"
fi

# Check Dockerfile optimization
echo -e "\n${BLUE}🐳 Checking Docker optimization:${NC}"

if [ -f "Dockerfile" ]; then
    echo -e "${GREEN}✅ Dockerfile found${NC}"
    
    # Check for multi-stage build
    if grep -q "FROM.*AS builder" "Dockerfile"; then
        echo -e "${GREEN}✅ Multi-stage build configured${NC}"
    else
        echo -e "${YELLOW}⚠️  Multi-stage build not detected${NC}"
    fi
    
    # Check for wheel building
    if grep -q "wheel" "Dockerfile"; then
        echo -e "${GREEN}✅ Wheel-based installation configured${NC}"
    else
        echo -e "${YELLOW}⚠️  Wheel optimization not detected${NC}"
    fi
else
    echo -e "${RED}❌ Dockerfile not found${NC}"
fi

# Check .dockerignore
if [ -f ".dockerignore" ]; then
    echo -e "${GREEN}✅ .dockerignore file exists${NC}"
    
    ignore_count=$(wc -l < .dockerignore)
    echo -e "   • Ignoring ${ignore_count} patterns to reduce build context"
else
    echo -e "${YELLOW}⚠️  .dockerignore file missing${NC}"
    echo -e "${YELLOW}   Consider creating one to reduce build context size${NC}"
fi

# Summary
echo -e "\n${BLUE}📊 Configuration Summary:${NC}"
echo -e "${BLUE}═══════════════════════════╤═══════════════════════════${NC}"
echo -e "${BLUE}Extended Timeout (20min)   │ $([ -f ".ebextensions/00_timeout.config" ] && grep -q "Timeout: 1200" ".ebextensions/00_timeout.config" && echo -e "${GREEN}✅ Active${NC}" || echo -e "${RED}❌ Missing${NC}")${BLUE}"
echo -e "${BLUE}Docker Daemon Timeout      │ $([ -f ".ebextensions/00_timeout.config" ] && grep -q "DockerDaemonTimeout:" ".ebextensions/00_timeout.config" && echo -e "${GREEN}✅ Active${NC}" || echo -e "${RED}❌ Missing${NC}")${BLUE}"
echo -e "${BLUE}Rolling Deployment         │ $([ -f ".ebextensions/00_timeout.config" ] && grep -q "DeploymentPolicy: Rolling" ".ebextensions/00_timeout.config" && echo -e "${GREEN}✅ Active${NC}" || echo -e "${RED}❌ Missing${NC}")${BLUE}"
echo -e "${BLUE}Multi-stage Docker Build   │ $([ -f "Dockerfile" ] && grep -q "FROM.*AS builder" "Dockerfile" && echo -e "${GREEN}✅ Active${NC}" || echo -e "${YELLOW}⚠️  Check${NC}")${BLUE}"
echo -e "${BLUE}Build Context Optimization │ $([ -f ".dockerignore" ] && echo -e "${GREEN}✅ Active${NC}" || echo -e "${YELLOW}⚠️  Missing${NC}")${BLUE}"
echo -e "${BLUE}═══════════════════════════╧═══════════════════════════${NC}"

# Recommendations
echo -e "\n${BLUE}💡 Recommendations:${NC}"

if [ ! -f ".ebextensions/00_timeout.config" ] || ! grep -q "Timeout: 1200" ".ebextensions/00_timeout.config"; then
    echo -e "${YELLOW}• Configure 20-minute timeout to handle long Docker builds${NC}"
fi

if [ ! -f "Dockerfile" ] || ! grep -q "FROM.*AS builder" "Dockerfile"; then
    echo -e "${YELLOW}• Implement multi-stage Docker build for faster deployments${NC}"
fi

if [ ! -f ".dockerignore" ]; then
    echo -e "${YELLOW}• Create .dockerignore to reduce build context size${NC}"
fi

echo -e "\n${GREEN}🚀 Ready for optimized deployment with extended timeout!${NC}"

# Show deployment command
echo -e "\n${BLUE}Next steps:${NC}"
echo -e "1. Run: ${YELLOW}./deploy_with_timeout.sh${NC}"
echo -e "2. Monitor build progress with timeout warnings"
echo -e "3. Check logs if deployment exceeds 20-minute limit"
