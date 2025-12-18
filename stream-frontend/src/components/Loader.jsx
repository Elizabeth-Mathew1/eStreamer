import { useState, useEffect } from 'react'
import { Box, Text } from '@chakra-ui/react'
import '../index.css'

const LOADING_MESSAGES = [
  'Starting chat ingestion...',
  'Batching chats...',
  'Processing chats for spice...',
  'Fetching from database...',
]

const Loader = () => {
  const [currentMessageIndex, setCurrentMessageIndex] = useState(0)

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentMessageIndex((prev) => (prev + 1) % LOADING_MESSAGES.length)
    }, 5000) // 5 seconds

    return () => clearInterval(interval)
  }, [])

  return (
    <Box display="flex" flexDirection="column" justifyContent="center" alignItems="center" mt="30vh" gap={4}>
      <Box className="loader" />
      <Text color="blue.300" fontSize="14px">
        {LOADING_MESSAGES[currentMessageIndex]}
      </Text>
    </Box>
  )
}

export default Loader

