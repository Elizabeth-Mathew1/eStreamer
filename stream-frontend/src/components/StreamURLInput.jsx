import React from 'react'
import { useSelector, useDispatch } from 'react-redux'
import {
  Box,
  Input,
  Button,
  Flex,
  Text,
} from '@chakra-ui/react'
import { setVideoUrl } from '../features/stream/streamSlice'
import { useStartStreamMutation } from '../features/api/apiSlice'
import { IoIosLink } from 'react-icons/io'

// Extract video ID from YouTube URL
const extractVideoId = (url) => {
  if (!url) return null
  const match = url.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&\n?#]+)/)
  return match ? match[1] : null
}

const StreamURLInput = () => {
  const dispatch = useDispatch()
  const videoUrl = useSelector((state) => state.stream.videoUrl)
  const [startStream, { isLoading, error }] = useStartStreamMutation()

  const handleUrlChange = (e) => {
    dispatch(setVideoUrl(e.target.value))
  }

  const handleAnalyze = async () => {
    const videoId = extractVideoId(videoUrl)
    if (!videoId) {
      alert('Please enter a valid YouTube URL')
      return
    }

    try {
      // start background stream chats ingestion
      const result = await startStream(videoId).unwrap()
      console.log('Stream started:', result)
    } catch (err) {
      console.error('Error starting stream:', err)
      alert(err?.data?.error || 'Failed to start stream')
    }
  }

  return (
    <Box>
      <Text color="white" mb={4} fontSize="16px" fontWeight="semibold">
        YouTube Live Stream URL
      </Text>
      <Flex gap={3} align="center">
        <Box position="relative" flex={1}>
          <Box
            position="absolute"
            left={3}
            top="50%"
            transform="translateY(-50%)"
            color="blue.300"
            zIndex={1}
            pointerEvents="none"
          >
            <IoIosLink size={26} mr={2}/>
          </Box>
          <Input
            placeholder="https://www.youtube.com/watch?v=nJKDNPs0wP8"
            value={videoUrl}
            onChange={handleUrlChange}
            variant="outline"
            border="2px solid"
            borderColor="gray.600"
            color="white"
            borderRadius="xl"
            pl={12}
            py={4}
            height="54px"
            _focus={{
              border: '2px solid',
              borderColor: '#9f7aea',
              outline: 'none',
            }}
          />
        </Box>
        <Button
          onClick={handleAnalyze}
          isLoading={isLoading}
          loadingText="Analyzing..."
          background="linear-gradient(to right,rgb(76, 136, 233), #9f7aea)"
          color="white"
          fontWeight="bold"
          borderRadius="xl"
          px={6}
          height="54px"
          border="none"
          isDisabled={!videoUrl || isLoading}
          _hover={{
            background: 'linear-gradient(to left, rgb(76, 136, 233), #9f7aea)',
          }}
        >
          Analyse
        </Button>
      </Flex>
    </Box>
  )
}

export default StreamURLInput

