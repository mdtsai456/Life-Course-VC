import '@testing-library/jest-dom/vitest'

if (typeof URL.createObjectURL === 'undefined') {
  let counter = 0
  URL.createObjectURL = () => `blob:mock-${++counter}`
  URL.revokeObjectURL = () => {}
}
