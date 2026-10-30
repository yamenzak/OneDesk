import vue from '@vitejs/plugin-vue'
import { sheetSeams } from './src/sheet/seams.mjs'
import { writerSeams } from './src/writer/seams.mjs'
import { slideSeams } from './src/slide/seams.mjs'

export default {
  plugins: [slideSeams, sheetSeams, writerSeams, vue()],
  test: { environment: 'jsdom', include: ['src/**/*.test.{js,ts}'] },
}
