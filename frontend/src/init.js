import { setup } from './lib/allauth'

export function init() {
  console.log('Initializing application...');
  // Configure for your environment
  setup('browser', '/_allauth/browser/v1', true);
  console.log('Application initialized');
}