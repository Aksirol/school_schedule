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

// Перехоплювач відповідей для автоматичного оновлення токена
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // Якщо помилка 401 (Unauthorized) і ми ще не намагалися оновити токен для цього запиту
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const refreshToken = Cookies.get('refresh_token');

        if (!refreshToken) {
          throw new Error('Немає refresh токена');
        }

        // Робимо запит на оновлення токена
        // Використовуємо axios напряму, щоб уникнути зациклення в нашому інтерцепторі api
        const response = await axios.post(`${api.defaults.baseURL}/auth/refresh/`, {
          refresh: refreshToken,
        });

        const { access } = response.data;

        // Зберігаємо новий access_token
        Cookies.set('access_token', access, { expires: 1 }); // 1 день

        // Оновлюємо заголовок в оригінальному запиті та повторюємо його
        originalRequest.headers.Authorization = `Bearer ${access}`;
        return api(originalRequest);

      } catch (refreshError) {
        // Якщо refresh_token також прострочений або недійсний
        Cookies.remove('access_token');
        Cookies.remove('refresh_token');

        // Перенаправляємо на сторінку логіну (тільки якщо код виконується в браузері)
        if (typeof window !== 'undefined') {
          window.location.href = '/login';
        }
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

export default api;