import {StrictMode} from 'react';
import {createRoot} from 'react-dom/client';
import {BrowserRouter} from 'react-router';
import App from './App.tsx';
import './index.css';
import {ThemeProvider, applyThemeClass, resolveTheme} from './utils/useTheme.tsx';

// Gắn class chế độ tối trước khi render để F5 ở trang chủ không bị nháy trắng.
applyThemeClass(resolveTheme());

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <ThemeProvider>
        <App />
      </ThemeProvider>
    </BrowserRouter>
  </StrictMode>
);
