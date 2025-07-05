import { createContext, useEffect, useReducer, useRef } from 'react';
import axiosInstance from '../services/axios';
import { setSession, resetSession } from '../utils/sessions';
import validateToken from '../utils/jwt';

const initialState = {
    isAuthenticated: false,
    isInitialized: false,
    user: null,
};

export const AuthContext = createContext({
    ...initialState,
    login: () => Promise.resolve(),
    logout: () => Promise.resolve(),
});

const handlers = {
    INITIALIZE: (state, action) => {
        const { isAuthenticated, user } = action.payload;
        return {
            ...state,
            isAuthenticated,
            isInitialized: true,
            user
        };
    },
    LOGIN: (state, action) => {
        const { user } = action.payload;
        return {
            ...state,
            isAuthenticated: true,
            user
        };
    },
    LOGOUT: (state) => {
        return {
            ...state,
            isAuthenticated: false,
            user: null
        };
    }
};

const reducer = (state, action) => 
    handlers[action.type] ? handlers[action.type](state, action) : state;

export const AuthProvider = (props) => {
    const { children } = props;
    const [state, dispatch] = useReducer(reducer, initialState);
    const isInitialized = useRef(false);

    useEffect(() => {
        // Prevent multiple initialization calls
        if (isInitialized.current) {
            return;
        }
        
        const initialize = async () => {
            try {
                const accessToken = localStorage.getItem('accessToken');
                if (accessToken && validateToken(accessToken)) {
                    setSession(accessToken);
                    const response = await axiosInstance.get('/user/me');
                    const { data: user } = response.data;
                    dispatch({
                        type: 'INITIALIZE',
                        payload: {
                            isAuthenticated: true,
                            user
                        }
                    });
                } else {
                    // Clear invalid token if it exists
                    if (accessToken) {
                        resetSession();
                    }
                    dispatch({
                        type: 'INITIALIZE',
                        payload: {
                            isAuthenticated: false,
                            user: null
                        }
                    });
                }
            } catch (error) {
                console.error('Auth initialization error:', error);
                resetSession(); // Clear potentially invalid session
                dispatch({
                    type: 'INITIALIZE',
                    payload: {
                        isAuthenticated: false,
                        user: null
                    }
                });
            }
        };

        initialize();
        isInitialized.current = true;
    }, []);

    const getTokens = async (email, password) => {
        const formData = new FormData();
        formData.append('username', email);
        formData.append('password', password);
        try {
            const response = await axiosInstance.post('/auth/login', formData);
            setSession(response.data.accessToken, response.data.refreshToken);  
        } catch (error) {
            throw error;
        }
    };

    const login = async (email, password) => {
        try {
            await getTokens(email, password);
            const response = await axiosInstance.get('/user/me');
            const { data: user } = response.data;
            dispatch({
                type: 'LOGIN',
                payload: { user }
            });
        } catch (error) {
            return Promise.reject(error);
        }
    };

    const logout = async () => {
        resetSession();
        dispatch({ type: 'LOGOUT' });
    };

    return (
        <AuthContext.Provider
            value={{
                ...state,
                login,
                logout,
            }}
        >
            {children}
        </AuthContext.Provider>
    );
};

export default AuthProvider;