import axios from 'axios';
import Cookies from 'js-cookie';

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost/api',
});

// Додаємо JWT токен до кожного запиту
api.interceptors.request.use((config) => {
  const token = Cookies.get('access_token');
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Обробка помилок (наприклад, закінчення дії токена)
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    // Тут в майбутньому можна додати логіку автоматичного refresh-токена
    if (error.response?.status === 401) {
      Cookies.remove('access_token');
      Cookies.remove('refresh_token');
      window.location.href = '/login'; // Перекидаємо на логін
    }
    return Promise.reject(error);
  }
);

export default api;