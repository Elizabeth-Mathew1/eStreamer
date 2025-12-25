import React from 'react'
import { useSelector, useDispatch } from 'react-redux'
import {
  Box,
  Input,
  Button,
  Flex,
  Text,
} from '@chakra-ui/react'
import { setVideoUrl, setIsAnalyzing, setAnalyticsData } from '../features/stream/streamSlice'
import { useStartStreamMutation, useLazyGetAnalyticsQuery } from '../features/api/apiSlice'
import { IoIosLink } from 'react-icons/io'
import { LOADING_STATUS } from '../common'

// Extract video ID from YouTube URL
const extractVideoId = (url) => {
  if (!url) return null
  const match = url.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&\n?#]+)/)
  return match ? match[1] : null
}

const StreamURLInput = () => {
  const dispatch = useDispatch()
  const videoUrl = useSelector((state) => state.stream.videoUrl)
  const isAnalyzing = useSelector((state) => state.stream.isAnalyzing)
  const duration = useSelector((state) => state.stream.duration)
  const analyticsData = useSelector((state) => state.stream.analyticsData)

  // Extract video ID from URL
  const videoId = extractVideoId(videoUrl)

  const [startStream, { error }] = useStartStreamMutation()
  
  // Use lazy query - manual trigger, no auto-fetch
  const [triggerAnalytics, { isLoading: isGettingAnalytics}] = useLazyGetAnalyticsQuery()

  const handleUrlChange = (e) => {
    dispatch(setVideoUrl(e.target.value))
  }

  const handleAnalyze = async () => {
    // Prevent multiple clicks
    if (isAnalyzing == LOADING_STATUS.LOADING) {
      return
    }

    const videoId = extractVideoId(videoUrl)
    if (!videoId) {
      alert('Please enter a valid YouTube URL')
      return
    }

    // Set analyzing to true
    dispatch(setIsAnalyzing(LOADING_STATUS.LOADING))

    try {
      // start background stream chats ingestion
      const result = await startStream(videoId).unwrap()
      console.log('Stream started:', result)
    } catch (err) {
      console.error('Error starting stream:', err)
      alert(err?.data?.error || 'Failed to start stream')
      dispatch(setIsAnalyzing(false))
      return
    }


    // Set analyzing to false after 1 minute (60 seconds)
    setTimeout(() => {
      dispatch(setIsAnalyzing(LOADING_STATUS.SUCCESS))
    }, 3000)

    // Enable analytics fetching after a short delay 
    if (videoId && duration) {
      setTimeout(async () => {
        try {
          const analyticsResult = await triggerAnalytics({ 
            live_chat_id: 'Cg0KC25KS0ROUHMwd1A4KicKGFVDV1d3WGdnQ0F2M3BtN2dSLWk4OFAyURILbkpLRE5QczB3UDg', 
            duration: duration 
          }).unwrap()

          dispatch(setAnalyticsData(analyticsResult))

        } catch (err) {
          alert(err?.data?.error || 'Failed to fetch analytics')
        }
      }, 2000)
    }
  }

  
  const isAnalyzingLoading = isAnalyzing === LOADING_STATUS.LOADING
  

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
          loading={isAnalyzingLoading || isGettingAnalytics}
          loadingText="Analysing..."
          background={isAnalyzingLoading ? 'gray.600' : 'linear-gradient(to right,rgb(76, 136, 233), #9f7aea)'}
          color="white"
          fontWeight="bold"
          borderRadius="xl"
          px={6}
          height="54px"
          border="none"
          disabled={isAnalyzingLoading || isGettingAnalytics}
          cursor={isAnalyzingLoading ? 'not-allowed' : 'pointer'}
          _hover={{
            background: isAnalyzingLoading ? 'gray.500' : 'linear-gradient(to left, rgb(76, 136, 233), #9f7aea)',
          }}
        >
          {isAnalyzingLoading ? 'Analysing...' : 'Analyse'}
        </Button>
      </Flex>
    </Box>
  )
}

export default StreamURLInput

