import '@testing-library/jest-dom/vitest'

let counter = 0

if (typeof URL.createObjectURL === 'undefined') {
  URL.createObjectURL = () => `blob:mock-${++counter}`
}

if (typeof URL.revokeObjectURL === 'undefined') {
  URL.revokeObjectURL = () => {}
}
