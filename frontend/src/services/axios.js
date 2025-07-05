import axios from 'axios';

const baseURL = 'http://localhost:8000/api/v1/';

const axiosInstance = axios.create({
  baseURL,
});

axiosInstance.interceptors.request.use(
    (response) => response,
    (error) => {
        return Promise.reject(error);
    }
)

export default axiosInstance;