import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
// React 보다 먼저 실행되어야 한다. 크롬의 beforeinstallprompt 는 딱 한 번
// 발화하고, 그 시점이 마운트보다 이를 수 있다. 자세한 이유는 모듈 주석 참고.
import './utils/installPrompt'
import App from './App.jsx'

createRoot(document.getElementById('root')).render(
    <StrictMode>
        <App />
    </StrictMode>
)