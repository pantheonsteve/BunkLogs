#!/usr/bin/env node

/**
 * Debug script to check date handling in counselor log submission
 */

console.log('=== Counselor Log Date Debug ===\n');

// Test current date logic
const now = new Date();
const today = new Date().toISOString().split('T')[0];
const yesterday = new Date();
yesterday.setDate(yesterday.getDate() - 1);
const yesterdayStr = yesterday.toISOString().split('T')[0];

const thirtyDaysAgo = new Date();
thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
const thirtyDaysAgoStr = thirtyDaysAgo.toISOString().split('T')[0];

const tomorrow = new Date();
tomorrow.setDate(tomorrow.getDate() + 1);
const tomorrowStr = tomorrow.toISOString().split('T')[0];

console.log('Current timezone:', Intl.DateTimeFormat().resolvedOptions().timeZone);
console.log('Current time:', now.toString());
console.log('Today (YYYY-MM-DD):', today);
console.log('Yesterday (YYYY-MM-DD):', yesterdayStr);
console.log('30 days ago (YYYY-MM-DD):', thirtyDaysAgoStr);
console.log('Tomorrow (YYYY-MM-DD):', tomorrowStr);

console.log('\n=== Validation Test ===');

// Test the validation logic from CounselorLogForm
function validateDate(testDate, userRole = 'Counselor') {
    const errors = [];
    
    if (userRole === 'Counselor') {
        if (testDate > today) {
            errors.push('Cannot create logs for future dates');
        }
        
        if (testDate < thirtyDaysAgoStr) {
            errors.push('You can only submit counselor logs for today\'s date or up to 30 days back');
        }
    }
    
    return errors;
}

// Test various dates
const testDates = [
    { date: tomorrowStr, label: 'Tomorrow' },
    { date: today, label: 'Today' },
    { date: yesterdayStr, label: 'Yesterday' },
    { date: thirtyDaysAgoStr, label: '30 days ago (boundary)' },
    { date: new Date(thirtyDaysAgo.getTime() - 24*60*60*1000).toISOString().split('T')[0], label: '31 days ago (should fail)' }
];

testDates.forEach(test => {
    const errors = validateDate(test.date);
    console.log(`${test.label} (${test.date}): ${errors.length === 0 ? 'VALID' : 'INVALID - ' + errors.join(', ')}`);
});

console.log('\n=== Date Comparison Logic ===');
console.log('String comparison examples:');
console.log(`'${today}' > '${today}':`, today > today);
console.log(`'${yesterdayStr}' < '${today}':`, yesterdayStr < today);
console.log(`'${tomorrowStr}' > '${today}':`, tomorrowStr > today);
console.log(`'${thirtyDaysAgoStr}' < '${thirtyDaysAgoStr}':`, thirtyDaysAgoStr < thirtyDaysAgoStr);

// Test what happens if server/client timezone mismatch
console.log('\n=== Potential Issues ===');
console.log('If server is in different timezone, date strings might not match expectations');
console.log('Current local date parts:');
console.log('- Year:', now.getFullYear());
console.log('- Month:', now.getMonth() + 1);
console.log('- Day:', now.getDate());
console.log('- UTC Date:', now.toISOString().split('T')[0]);
console.log('- Local Date String:', now.toLocaleDateString('en-CA')); // YYYY-MM-DD format
