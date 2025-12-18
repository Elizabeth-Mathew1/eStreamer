import { Box, Container } from '@chakra-ui/react'
import MainInputBox from './components/MainInputBox'
import Loader from './components/Loader'

function App() {
  return (
    <Box minH="100vh" bg="0B0C0E" py={8} px={10} color="white">
      <Container maxW="container.lg">
        <MainInputBox />
        <Loader />
      </Container>
    </Box>
  )
}

export default App


