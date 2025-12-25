import { Box, Container } from '@chakra-ui/react'
import MainInputBox from './components/MainInputBox'
import Analytics from './components/Analytics'
import Loader from './components/Loader'
import { useSelector } from 'react-redux'



function App() {
  const isAnalyzing = useSelector((state) => state.stream.isAnalyzing)
  return (
    <Box minH="100vh" bg="0B0C0E" py={8} px={10} color="white">
      <Container maxW="container.lg">
        <MainInputBox />
        <Analytics />
      </Container>
    </Box>
  )
}

export default App


