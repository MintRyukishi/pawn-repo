import { jwtDecode } from 'jwt-decode'; 
const validateToken = (token) => {
    try {
        if (!token) {
            return false;
        }

        const now = Math.round(new Date().getTime() / 1000);
        const decodedToken = jwtDecode(token);  
        const isValid = decodedToken && now < decodedToken.exp;

        return isValid;
    } catch (error) {
        console.error('Token validation error:', error);
        return false;
    }
};

export default validateToken;