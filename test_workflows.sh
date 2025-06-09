#!/bin/bash

# BunkLogs - Test Signup and Password Reset Workflows
echo "🧪 Testing BunkLogs Signup and Password Reset Workflows"
echo "======================================================"

API_BASE="https://admin.bunklogs.net"
FRONTEND_BASE="https://clc.bunklogs.net"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0

run_test() {
    local test_name="$1"
    local test_command="$2"
    echo -e "\n${YELLOW}Testing: $test_name${NC}"
    
    if eval "$test_command"; then
        echo -e "${GREEN}✅ PASS: $test_name${NC}"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}❌ FAIL: $test_name${NC}"
        ((TESTS_FAILED++))
    fi
}

# Test 1: Backend Server Accessibility
run_test "Backend Server Accessibility" "curl -s -o /dev/null -w '%{http_code}' $API_BASE/api/v1/ | grep -q '200'"

# Test 2: Frontend Server Accessibility  
run_test "Frontend Server Accessibility" "curl -s -o /dev/null -w '%{http_code}' $FRONTEND_BASE | grep -q '200'"

# Test 3: User Creation API
run_test "User Creation API" 'curl -s -X POST $API_BASE/api/v1/users/create/ -H "Content-Type: application/json" -d "{\"email\":\"test$(date +%s)@example.com\",\"first_name\":\"Test\",\"last_name\":\"User\",\"password\":\"testpass123\"}" | grep -q "Counselor"'

# Test 4: Duplicate Email Handling
run_test "Duplicate Email Handling" 'curl -s -X POST $API_BASE/api/v1/users/create/ -H "Content-Type: application/json" -d "{\"email\":\"test@example.com\",\"first_name\":\"Duplicate\",\"last_name\":\"User\",\"password\":\"testpass123\"}" | grep -q "already exists"'

# Test 5: Password Reset API
run_test "Password Reset API" 'curl -s -X POST $API_BASE/_allauth/browser/v1/auth/password/request -H "Content-Type: application/json" -H "Accept: application/json" -d "{\"email\":\"test@example.com\"}" | grep -q "200"'

# Test 6: Login API
run_test "Login API" 'curl -s -X POST $API_BASE/api/auth/token/ -H "Content-Type: application/json" -d "{\"email\":\"testuser2@example.com\",\"password\":\"testpassword123\"}" | grep -q "access"'

# Test 7: Signup Page Accessibility
run_test "Signup Page Accessibility" "curl -s -o /dev/null -w '%{http_code}' $FRONTEND_BASE/signup | grep -q '200'"

# Test 8: Reset Password Page Accessibility
run_test "Reset Password Page Accessibility" "curl -s -o /dev/null -w '%{http_code}' $FRONTEND_BASE/reset-password | grep -q '200'"

# Test 9: Signin Page Accessibility
run_test "Signin Page Accessibility" "curl -s -o /dev/null -w '%{http_code}' $FRONTEND_BASE/signin | grep -q '200'"

# Test 10: Mailpit Service Accessibility
run_test "Mailpit Service Accessibility" "curl -s -o /dev/null -w '%{http_code}' http://localhost:8025 | grep -q '200'"

# Summary
echo -e "\n${YELLOW}======================================================"
echo "Test Summary"
echo "=====================================================${NC}"
echo -e "${GREEN}Tests Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Tests Failed: $TESTS_FAILED${NC}"

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "\n${GREEN}🎉 All tests passed! The signup and password reset workflows are ready for production.${NC}"
    exit 0
else
    echo -e "\n${RED}❌ Some tests failed. Please review the issues above.${NC}"
    exit 1
fi
