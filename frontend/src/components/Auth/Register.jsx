import { Flex, useColorModeValue, Heading, FormControl, Input, FormErrorMessage, Button } from '@chakra-ui/react';
import { useForm } from 'react-hook-form';
import { useNavigate } from 'react-router-dom';
import ThemeToggler from '../Theme/ThemeToggler';

export const Register = () => {
    const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm();
    
    const onSubmit = async (values) => {
        console.log(values);
    };
    
    const navigate = useNavigate();

    return (
        <Flex height="100vh" justifyContent="center" alignItems="center">
            <Flex 
                direction="column"
                alignItems="center"
                background={useColorModeValue('gray.100', 'gray.700')}
                p={12}
                rounded={6}
                maxWidth="400px"
                width="100%"
            >
                <Heading mb={6}>
                    Register
                </Heading>
                
                <form onSubmit={handleSubmit(onSubmit)} style={{ width: '100%' }}>
                    <FormControl isInvalid={errors.username}>
                        <Input
                            placeholder="Username"
                            type="text"
                            autoFocus
                            background={useColorModeValue('gray.300', 'gray.600')}
                            size="lg"
                            mt={6}
                            {...register('username', {
                                required: 'Username is required',
                                minLength: {
                                    value: 3,
                                    message: 'Username must be at least 3 characters'
                                },
                                maxLength: {
                                    value: 20,
                                    message: 'Username must be less than 20 characters'
                                },
                                pattern: {
                                    value: /^[a-zA-Z0-9_]+$/,
                                    message: 'Username can only contain letters, numbers, and underscores'
                                }
                            })}
                        />
                        <FormErrorMessage>
                            {errors.username && errors.username.message}
                        </FormErrorMessage>
                    </FormControl>
                    
                    <FormControl isInvalid={errors.email}>
                        <Input
                            placeholder="Email"
                            type="email"
                            background={useColorModeValue('gray.300', 'gray.600')}
                            size="lg"
                            mt={6}
                            {...register('email', {
                                required: 'Email is required',
                                pattern: {
                                    value: /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/,
                                    message: 'Invalid email address'
                                }
                            })}
                        />
                        <FormErrorMessage>
                            {errors.email && errors.email.message}
                        </FormErrorMessage>
                    </FormControl>
                    
                    <FormControl isInvalid={errors.password}>
                        <Input
                            placeholder="Password"
                            type="password"
                            background={useColorModeValue('gray.300', 'gray.600')}
                            size="lg"
                            mt={6}
                            {...register('password', {
                                required: 'Password is required',
                                minLength: {
                                    value: 8,
                                    message: 'Password must be at least 8 characters'
                                },
                                pattern: {
                                    value: /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]/,
                                    message: 'Password must contain uppercase, lowercase, number and special character'
                                }
                            })}
                        />
                        <FormErrorMessage>
                            {errors.password && errors.password.message}
                        </FormErrorMessage>
                    </FormControl>
                    
                    <Button
                        type="submit"
                        colorScheme="green"
                        variant="outline"
                        size="lg"
                        width="100%"
                        mt={6}
                        mb={6}
                        isLoading={isSubmitting}
                        loadingText="Registering..."
                    >
                        Register
                    </Button>
                </form>
                
                <ThemeToggler showLabel={true}/>
                
                <Button
                    colorScheme="gray"
                    variant="outline"
                    size="lg"
                    width="100%"
                    mt={6}
                    onClick={() => navigate('/login', { replace: true })}
                >
                    Login Instead
                </Button>
            </Flex>
        </Flex>
    );
};

export default Register;