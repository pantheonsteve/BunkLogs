# 🔍 Password Reset Testing & Debugging Workflow

## 🎯 **TESTING WORKFLOW**

### **Step 1: Test in Production Frontend**
1. **Go to your live frontend**: `https://clc.bunklogs.net/accounts/password/reset`
2. **Enter your email**: `stevebresnick@gmail.com`
3. **Submit the form**
4. **Check result**: Should see success message or error

### **Step 2: Check Email Delivery**
1. **Check your email inbox** for password reset email
2. **Look for sender**: Should be from your configured email domain
3. **Check spam folder** if not in inbox
4. **Note the reset link format** in the email

### **Step 3: Test Reset Link**
1. **Click the reset link** from email
2. **Should redirect to**: `https://clc.bunklogs.net/accounts/password/reset/key/SOME_KEY`
3. **Enter new password** and confirm
4. **Submit form** to complete reset

---

## 🐛 **DEBUGGING WORKFLOW WITH ME**

### **If Step 1 Fails (Form Submission)**

**Tell me what happens, then I'll run:**

```bash
# I'll check frontend console errors
# You run this in browser dev tools (F12):
console.log('Testing CSRF token access...');
const csrfToken = document.cookie.match(/(?:^|; )__Secure-csrftoken=([^;]*)/)?.[1] || 
                  document.cookie.match(/(?:^|; )csrftoken=([^;]*)/)?.[1];
console.log('CSRF Token found:', csrfToken ? 'YES' : 'NO');
```

**I'll then debug backend:**
```bash
# Check if request is reaching backend
curl -v -c debug.txt -b debug.txt \
  -H "Origin: https://clc.bunklogs.net" \
  "https://admin.bunklogs.net/_allauth/browser/v1/config"

# Test password reset with proper headers
curl -v -c debug.txt -b debug.txt \
  -X POST \
  -H "Content-Type: application/json" \
  -H "Origin: https://clc.bunklogs.net" \
  -H "X-CSRFToken: EXTRACTED_TOKEN" \
  -d '{"email": "stevebresnick@gmail.com"}' \
  "https://admin.bunklogs.net/_allauth/browser/v1/auth/password/request"
```

### **If Step 2 Fails (No Email)**

**I'll check email configuration:**
```bash
# Check production email settings
# I'll examine backend logs and email service status
# Check Mailgun/email provider dashboard
```

### **If Step 3 Fails (Reset Link Issues)**

**I'll debug URL configuration:**
```bash
# Check AllAuth frontend URL configuration
# Verify reset key validation
# Test the complete reset flow
```

---

## 📋 **TELL ME THESE DETAILS**

When testing, report back:

### **Frontend Behavior:**
- [ ] **Form loads?** (Yes/No)
- [ ] **Submit button works?** (Yes/No) 
- [ ] **Error messages shown?** (What message?)
- [ ] **Browser console errors?** (F12 → Console tab)
- [ ] **Network tab shows requests?** (F12 → Network tab)

### **Email Delivery:**
- [ ] **Email received?** (Yes/No)
- [ ] **How long did it take?** (Minutes)
- [ ] **Sender address?** (What address?)
- [ ] **Reset link format?** (What domain?)

### **Reset Completion:**
- [ ] **Reset link works?** (Yes/No)
- [ ] **Password form appears?** (Yes/No)
- [ ] **Password change succeeds?** (Yes/No)

---

## 🔧 **MY DEBUGGING TOOLS**

Based on your feedback, I'll use:

### **Backend API Testing:**
```bash
# Real-time API testing
curl -v [various AllAuth endpoints]

# Check backend logs
# Verify email service status
# Test CSRF token flow
```

### **Frontend Integration Testing:**
```bash
# Create test HTML pages
# Simulate browser requests
# Test cookie/token handling
```

### **Email Service Testing:**
```bash
# Check email service configuration
# Test email delivery pipeline
# Verify template rendering
```

---

## 🚀 **QUICK START**

**Right now, go test:**
1. **Visit**: `https://clc.bunklogs.net/accounts/password/reset`
2. **Try password reset** with your email
3. **Come back and tell me exactly what happens**

**I'll be ready to debug any issues you encounter!**

---

## ⚡ **COMMON ISSUES & MY FIXES**

| Issue | What I'll Check | How I'll Fix |
|-------|----------------|--------------|
| Form doesn't submit | CSRF tokens, CORS | Backend config fixes |
| 403 Forbidden | CSRF middleware | Settings updates |
| No email received | Email service config | Provider settings |
| Reset link broken | URL configuration | AllAuth settings |
| Frontend errors | Console logs | JavaScript fixes |

**Ready to debug with you! Just tell me what you see.** 🔍
