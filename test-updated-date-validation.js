#!/usr/bin/env node

/**
 * Test the updated date validation logic
 */

console.log('=== Updated Counselor Log Date Validation Test ===\n');

// Updated date logic (matching the fix)
function getLocalDateString(date = new Date()) {
    return date.getFullYear() + '-' + 
           String(date.getMonth() + 1).padStart(2, '0') + '-' + 
           String(date.getDate()).padStart(2, '0');
}

const now = new Date();
const today = getLocalDateString(now);
const yesterday = getLocalDateString(new Date(now.getTime() - 24*60*60*1000));
const tomorrow = getLocalDateString(new Date(now.getTime() + 24*60*60*1000));

console.log('Current time:', now.toString());
console.log('Today (local):', today);
console.log('Yesterday (local):', yesterday);
console.log('Tomorrow (local):', tomorrow);

// Test validation with the new logic
function validateCounselorDate(testDate) {
    const errors = [];
    
    const thirtyDaysAgo = new Date();
    thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
    const thirtyDaysAgoStr = getLocalDateString(thirtyDaysAgo);
    
    if (testDate > today) {
        errors.push('Cannot create logs for future dates');
    }
    
    if (testDate < thirtyDaysAgoStr) {
        errors.push('You can only submit counselor logs for today\'s date or up to 30 days back');
    }
    
    return errors;
}

console.log('\n=== Validation Results ===');
const testCases = [
    { date: tomorrow, label: 'Tomorrow' },
    { date: today, label: 'Today' },
    { date: yesterday, label: 'Yesterday' }
];

testCases.forEach(test => {
    const errors = validateCounselorDate(test.date);
    console.log(`${test.label} (${test.date}): ${errors.length === 0 ? '✅ VALID' : '❌ INVALID - ' + errors.join(', ')}`);
});

// Also test the specific case that might be failing
console.log('\n=== Real-world Test Case ===');
console.log('If counselors are on July 11 (local time) trying to submit for July 11:');
const july11 = '2025-07-11';
const july11Errors = validateCounselorDate(july11);
console.log(`July 11 log submission: ${july11Errors.length === 0 ? '✅ SHOULD WORK' : '❌ BLOCKED - ' + july11Errors.join(', ')}`);
