import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Login } from './components/Auth/Login';
import { Register } from './components/Auth/Register';
import { AuthProvider } from './context/JWTAuthContext';
import { Flex, Spinner } from '@chakra-ui/react';
import { useContext } from 'react';
import { AuthContext } from './context/JWTAuthContext';

const AppContent = () => {
  const auth = useContext(AuthContext);

  if (!auth.isInitialized) {
    return (
      <Flex height="100vh" justifyContent="center" alignItems="center">
        <Spinner 
          thickness='4px'
          speed='0.65s'
          emptyColor='green.200'
          size='xl'
          color='green.500'
        />
      </Flex>
    );
  }

  return (
    <Routes>
      <Route path="/" element={<div>Home Page</div>} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="*" element={<Navigate to="/" />} />
    </Routes>
  );
};

function App() {
  return (
    <AuthProvider>
      <Router>
        <AppContent />
      </Router>
    </AuthProvider>
  );
}

export default App;