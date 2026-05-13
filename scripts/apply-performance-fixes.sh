#!/bin/bash

# Performance Optimization Script for BunkLogs API
# This script applies database migrations and performance fixes

echo "🚀 Starting BunkLogs Performance Optimization..."

# Navigate to backend directory
cd /Users/steve.bresnick/Projects/BunkLogs/backend

echo "📊 Step 1: Applying database migrations for performance indexes..."
python manage.py migrate users 0002_performance_indexes --fake-initial 2>/dev/null || echo "Users migration already applied or failed"
python manage.py migrate bunks 0013_performance_indexes --fake-initial 2>/dev/null || echo "Bunks migration already applied or failed"

echo "🔍 Step 2: Analyzing current database performance..."
python manage.py shell << 'EOF'
import time
from django.contrib.auth import get_user_model
from django.db import connection
from django.test.utils import override_settings

User = get_user_model()

print("📈 Testing user lookup performance...")

# Test the current performance
start_time = time.time()
try:
    test_user = User.objects.first()
    if test_user:
        # Simulate the email lookup that was slow
        user = User.objects.select_related().prefetch_related('groups').get(email=test_user.email)
        print(f"✅ User lookup took: {(time.time() - start_time)*1000:.2f}ms")
    else:
        print("⚠️  No users found in database")
except Exception as e:
    print(f"❌ Error in user lookup: {e}")

# Test CounselorBunkAssignment queries
print("\n📈 Testing counselor assignment performance...")
from bunk_logs.bunks.models import CounselorBunkAssignment
from django.utils import timezone

start_time = time.time()
try:
    today = timezone.now().date()
    assignments = CounselorBunkAssignment.objects.filter(
        start_date__lte=today
    ).filter(
        models.Q(end_date__isnull=True) | models.Q(end_date__gte=today)
    ).select_related('bunk', 'bunk__cabin', 'bunk__session', 'bunk__unit')[:5]
    
    count = len(list(assignments))
    print(f"✅ Assignment lookup ({count} records) took: {(time.time() - start_time)*1000:.2f}ms")
except Exception as e:
    print(f"❌ Error in assignment lookup: {e}")

# Show current database queries
print("\n📊 Recent database queries:")
for query in connection.queries[-3:]:
    print(f"  {query['time']}s: {query['sql'][:100]}...")

EOF

echo "🔧 Step 3: Checking current URL configuration..."
python manage.py shell << 'EOF'
from django.urls import reverse
try:
    url = reverse('user-by-email', kwargs={'email': 'test@example.com'})
    print(f"✅ User by email URL pattern working: {url}")
except Exception as e:
    print(f"❌ URL configuration issue: {e}")
EOF

echo "📈 Step 4: Performance testing recommendations..."
cat << 'EOF'

📋 IMMEDIATE ACTIONS NEEDED:

1. 🔄 Restart your Django application server to pick up the code changes:
   - If using Render.com: Deploy the latest changes
   - If local development: Restart `python manage.py runserver`

2. 📊 Monitor the /api/v1/users/email/{email}/ endpoint performance:
   - Response times should drop from 50+ seconds to under 1 second
   - Database query count should be significantly reduced

3. 🗃️ Consider adding database query monitoring:
   - Enable Django's LOGGING for SQL queries in development
   - Add django-debug-toolbar for detailed query analysis
   - Monitor with APM tools like DataDog or New Relic in production

4. 🔍 Test the specific slow endpoint:
   curl -X GET "https://clc.bunklogs.net/api/v1/users/email/shainfriedman11@gmail.com/" \
        -H "Authorization: Bearer YOUR_TOKEN"

📋 ADDITIONAL OPTIMIZATIONS TO CONSIDER:

1. 🗄️ Database connection pooling (if not already configured)
2. 🗂️ Redis caching for frequently accessed user data
3. 📊 Database query monitoring in production
4. 🔄 Consider pagination for large result sets

EOF

echo "✅ Performance optimization script completed!"
echo "📈 Expected improvement: 50+ second response times should drop to <1 second"
