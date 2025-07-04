import { Switch, useColorMode, FormLabel } from '@chakra-ui/react';

export const ThemeToggler = ({ showLabel = false, ...rest }) => {
    const { colorMode, toggleColorMode } = useColorMode();

    return (
        <>
            {showLabel && (
                <FormLabel htmlFor="theme-toggler" mb={0}>
                    Enable Dark Mode
                </FormLabel>
            )}
            <Switch
                id="theme-toggler"
                size="sm"
                isChecked={colorMode === 'dark'}
                isDisabled={false}
                value={colorMode}
                colorScheme='green'
                mr={2}
                onChange={toggleColorMode}
                {...rest}
            />
        </>
    );
};

export default ThemeToggler;