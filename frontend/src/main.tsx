import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';

// Initialize auth store on app start
import { useAuthStore } from './stores/authStore';

// Initialize authentication state
const initializeAuth = () => {
  const { initialize } = useAuthStore.getState();
  initialize();
};

// Initialize the app
initializeAuth();

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);