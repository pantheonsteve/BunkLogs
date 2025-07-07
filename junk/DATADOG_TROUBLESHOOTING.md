# Datadog RUM Troubleshooting Guide 🔍

## ✅ Changes Made for Debugging

### 1. **Enhanced Environment Detection**
- Fixed Vite-specific environment variables (`import.meta.env.PROD` vs `NODE_ENV`)
- Added comprehensive logging to diagnose initialization issues
- Added force-enable flag for testing

### 2. **Better Error Handling**  
- Wrapped initialization in try-catch
- Added test event to verify connection
- Detailed console logging for all variables

### 3. **Production Configuration**
- Added `VITE_DATADOG_FORCE_ENABLE=true` for testing

## 🧪 Diagnostic Steps

### Step 1: Check Browser Console
After deploying, visit your production site and open browser dev tools:

**Look for these console logs:**
```
🔍 Datadog Environment Check: {
  isDevelopment: false,
  isProduction: true, 
  environment: "production",
  hasAppId: true,
  hasClientToken: true
}

✅ Datadog RUM initialized successfully: {
  environment: "production",
  service: "bunklogs-frontend", 
  version: "1.0.0"
}
```

### Step 2: Verify Network Requests
In browser dev tools → Network tab, look for:
- Requests to `browser-intake-datadoghq.com`
- Or requests to your configured Datadog site

### Step 3: Check Build Output
Verify environment variables are included in build:
```bash
npm run build
# Look for no errors mentioning missing env vars
```

## 🚨 Common Issues & Solutions

### Issue 1: Environment Variables Not Available
**Symptom**: Console shows `hasAppId: false`

**Solution**: 
- Verify `.env.production` has all VITE_DATADOG_* variables
- Ensure hosting platform (Render/Vercel/etc.) has environment variables set
- Check that variables start with `VITE_` prefix

### Issue 2: Wrong Environment Detection
**Symptom**: Shows `isProduction: false` in production

**Solution**: 
- Use `VITE_DATADOG_FORCE_ENABLE=true` to override
- Check your hosting platform's build configuration

### Issue 3: Network/CORS Issues
**Symptom**: Initialization succeeds but no network requests

**Solutions**:
- Check Content Security Policy (CSP) headers
- Verify no ad blockers are blocking Datadog domains
- Check if your hosting platform blocks external requests

### Issue 4: Datadog Account Configuration
**Symptom**: Requests go out but Datadog shows "not instrumented"

**Solutions**:
- Verify Application ID and Client Token are correct in Datadog dashboard
- Check if the RUM application is properly configured
- Ensure your domain is allowlisted in Datadog settings

## 🔧 Immediate Testing Steps

### 1. **Deploy Enhanced Version**
```bash
npm run build
# Deploy to your hosting platform
```

### 2. **Test in Production**
- Visit: https://clc.bunklogs.net
- Open browser dev tools → Console
- Look for the diagnostic logs

### 3. **Manual Verification**
Open browser console and run:
```javascript
// Check if Datadog is loaded
console.log('Datadog RUM:', window.DD_RUM);

// Send test event manually
if (window.DD_RUM) {
  DD_RUM.addAction('manual_test', { timestamp: Date.now() });
  console.log('Test event sent');
}
```

## 📊 Expected Timeline

- **Immediate**: Console logs should appear
- **1-2 minutes**: Network requests should start
- **5-10 minutes**: Data should appear in Datadog dashboard
- **15+ minutes**: Full session data and replays

## 🆘 If Still No Data

### Check Hosting Platform Environment Variables
Your hosting platform (Render, Vercel, etc.) needs these environment variables:

```bash
VITE_DATADOG_APPLICATION_ID=06f040c0-8a9c-4ca0-865c-9ad82ae138a0
VITE_DATADOG_CLIENT_TOKEN=pub61357afeab81d99906c5d9ddf48dfaf5
VITE_DATADOG_SITE=datadoghq.com
VITE_DATADOG_ENV=production
VITE_DATADOG_SERVICE=bunklogs-frontend
VITE_DATADOG_VERSION=1.0.0
VITE_DATADOG_FORCE_ENABLE=true
```

### Verify Datadog Dashboard
1. Go to Datadog → RUM → Applications
2. Find your application (bunklogs-frontend)
3. Check if it shows as "Instrumented"
4. Look for any error messages

### Alternative: Test Locally First
Temporarily add to `.env.local`:
```bash
VITE_DATADOG_FORCE_ENABLE=true
VITE_DATADOG_APPLICATION_ID=06f040c0-8a9c-4ca0-865c-9ad82ae138a0
VITE_DATADOG_CLIENT_TOKEN=pub61357afeab81d99906c5d9ddf48dfaf5
```

Run `npm run dev` and verify it works locally first.

The enhanced debugging will reveal exactly what's preventing the data flow! 🎯
