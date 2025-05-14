import { setup } from './lib/allauth'

export function init() {
  // Configure for your environment
  setup('browser', '/_allauth/browser/v1', true)
}