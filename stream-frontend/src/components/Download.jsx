// src/components/Download.jsx
import { useState, useEffect, useRef } from 'react'
import {
  Box,
  Button,
  Collapsible,
  Grid,
  Text,
  Image,
  Flex,
  Progress,
  Spinner,
} from '@chakra-ui/react'
import { FiDownload, FiChevronUp, FiChevronDown, FiTrendingUp } from 'react-icons/fi'
import { IoHappy, IoSad } from 'react-icons/io5'
import { RiEmotionNormalFill } from 'react-icons/ri'
import { useSelector } from 'react-redux'
import { useGetKeyMomentsMutation, usePollKeyMomentsStatusMutation } from '../features/api/apiSlice'

const getSentimentInfo = (avgSentiment) => {
const score = (avgSentiment >= -1 && avgSentiment <= 1) 
  ? Math.round(((avgSentiment + 1) / 2) * 100) // It's small (-1 to 1), so convert it
  : Math.round(avgSentiment);                  // It's big (0-100), so use as is
  
  let label, Icon
  if (score >= 80) {
    label = 'Highly Positive'
    Icon = IoHappy
  } else if (score >= 60) {
    label = 'Positive'
    Icon = IoHappy
  } else if (score >= 40) {
    label = 'Neutral'
    Icon = RiEmotionNormalFill
  } else if (score >= 20) {
    label = 'Negative'
    Icon = IoSad
  } else {
    label = 'Highly Negative'
    Icon = IoSad
  }
  
  return { score, label, Icon }
}

// Extract video ID from YouTube URL
const extractVideoId = (url) => {
  if (!url) return null
  const match = url.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&\n?#]+)/)
  return match ? match[1] : null
}

// Hardcoded thumbnails for circular queue
const THUMBNAILS = [
  'https://images.unsplash.com/photo-1478737270239-2f02b77fc618?w=300&h=200&fit=crop',
  'https://images.unsplash.com/photo-1581094271901-8022df4466f9?w=300&h=200&fit=crop',
  'https://images.unsplash.com/photo-1540575467063-178a50c2df87?w=300&h=200&fit=crop',
  'https://images.unsplash.com/photo-1505373877841-8d25f7d46678?w=300&h=200&fit=crop',
  'https://images.unsplash.com/photo-1517245386807-bb43f82c33c4?w=300&h=200&fit=crop',
]

const KeyMoments = () => {
  const [isOpen, setIsOpen] = useState(false)
  const [keyMoments, setKeyMoments] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [isPolling, setIsPolling] = useState(false)
  const [pollProgress, setPollProgress] = useState({ current: 0, total: 0, percent: 0, failed: 0 })
  const [error, setError] = useState(null)
  const [overallSentiment, setOverallSentiment] = useState(null)
  const pollingIntervalRef = useRef(null)
  
  const analyticsData = useSelector((state) => state.stream.analyticsData)
  const videoUrl = useSelector((state) => state.stream.videoUrl)
  
  const [getKeyMoments] = useGetKeyMomentsMutation()
  const [pollStatus] = usePollKeyMomentsStatusMutation()
  
  // Get sentiment data from API response or fallback to analyticsData
  const avgSentiment = overallSentiment !== null 
    ? overallSentiment 
    : (analyticsData?.avg_sentiment ?? 0)
  const { score, label, Icon } = getSentimentInfo(avgSentiment)

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current)
      }
    }
  }, [])

  const stopPolling = () => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current)
      pollingIntervalRef.current = null
    }
    setIsPolling(false)
  }

  const startPolling = async (videoUrl) => {
    setIsPolling(true)
    setPollProgress({ current: 0, total: 0, percent: 0, failed: 0 })

    const poll = async () => {
      try {
        const result = await pollStatus(videoUrl).unwrap()
        
        if (!result) {
          console.warn('Poll returned null, retrying...')
          return
        }

        // Status from backend is uppercase: COMPLETED, PARTIALLY_COMPLETED, FAILED, PENDING
        const status = result.status?.toUpperCase()
        const progress = result.progress || {}
        
        // Calculate progress from result data
        const current = progress.current || result.clips_completed_count || 0
        const total = progress.total || result.total_clips_expected || 1
        const failed = progress.failed || result.failed_clips || 0
        const percent = progress.percent || (total > 0 ? Math.round((current / total) * 100) : 0)
        
        // Update progress
        setPollProgress({
          current,
          total,
          percent,
          failed,
        })

        // Check if job is finished (any final status)
        if (status === 'COMPLETED' || status === 'PARTIALLY_COMPLETED' || status === 'FAILED') {
          stopPolling()
          setIsLoading(false)
          
          // Process the video URLs
          const videoUrls = result.video_urls || []
          
          if (status === 'FAILED' && videoUrls.length === 0) {
            // All clips failed
            setError('All video clips failed to process')
            setKeyMoments([])
            setIsOpen(true)
          } else if (videoUrls.length > 0) {
            // Process successful clips
            const processedMoments = videoUrls.map((url, index) => ({
              id: index + 1,
              clipUrl: url,
              sentiment: 0, // Individual sentiment not provided
              timestamp: `00:${String(Math.floor(index * 5)).padStart(2, '0')}:00`,
              duration: '00:03:00',
              title: `Key Moment ${index + 1}`,
              thumbnail: THUMBNAILS[index % THUMBNAILS.length],
            }))
            
            setKeyMoments(processedMoments)
            
            // Set overall sentiment if provided
            if (result.overall_sentiment !== undefined && result.overall_sentiment !== null) {
              setOverallSentiment(result.overall_sentiment)
            }
            
            // Show warning if partially completed
            if (status === 'PARTIALLY_COMPLETED') {
              setError(`Job completed with ${failed} clip(s) failed. Showing successful clips.`)
            }
            
            setIsOpen(true)
          } else {
            setError('No video URLs found in completed job')
            setIsOpen(true)
          }
        }
        // If status is PENDING or still processing, continue polling
      } catch (err) {
        console.error('Poll error:', err)
        
        // If it's a 404 or job not found, might mean job hasn't started yet
        if (err?.status === 404) {
          console.warn('Job not found yet, continuing to poll...')
          return
        }
        
        // Continue polling on other errors (might be temporary)
      }
    }

    // Poll immediately, then every 3 seconds
    poll()
    pollingIntervalRef.current = setInterval(poll, 3000)
  }

  const handleButtonClick = async () => {
    if (isOpen) {
      setIsOpen(false)
      stopPolling()
      return
    }

    if (!videoUrl) {
      alert('Please enter a valid YouTube URL first')
      return
    }

    // Extract video ID from URL
    const videoId = extractVideoId(videoUrl)
    if (!videoId) {
      alert('Please enter a valid YouTube URL first')
      return
    }

    // Use the full video URL for polling (backend expects live_video_url)
    const fullVideoUrl = videoUrl.startsWith('http') ? videoUrl : `https://www.youtube.com/watch?v=${videoId}`

    setIsLoading(true)
    setError(null)
    setKeyMoments([])
    setOverallSentiment(null)
    
    try {
      // Step 1: Trigger the download job - send just the video ID
      await getKeyMoments(videoId).unwrap()
      
      // Step 2: Start polling for status - send full video URL
      await startPolling(fullVideoUrl)
      
    } catch (err) {
      console.error('Error starting download:', err)
      setIsLoading(false)
      stopPolling()
      
      let errorMessage = 'Failed to start download'
      if (err?.data) {
        errorMessage = err.data.error || err.data.message || err.data.details || JSON.stringify(err.data)
      } else if (err?.message) {
        errorMessage = err.message
      }
      
      setError(errorMessage)
      setIsOpen(true)
    }
  }

  const handleDownload = (clipUrl, title) => {
    // Open in new tab or trigger download
    if (clipUrl) {
      window.open(clipUrl, '_blank')
    }
  }

  return (
    <Box mt={4}>
      <Button
        onClick={handleButtonClick}
        loading={isLoading || isPolling}
        loadingText={isPolling ? "Processing..." : "Starting..."}
        disabled={isLoading || isPolling}
        background="linear-gradient(to right, rgb(76, 136, 233), #9f7aea)"
        color="white"
        fontWeight="medium"
        borderRadius="lg"
        px={4}
        py={2}
        height="40px"
        fontSize="14px"
        _hover={{
          background: isLoading || isPolling 
            ? 'linear-gradient(to right, rgb(76, 136, 233), #9f7aea)' 
            : 'linear-gradient(to left, rgb(76, 136, 233), #9f7aea)',
        }}
      >
        <Flex align="center" gap={2}>
          Save All Key Moments
          {isOpen && !isPolling ? <FiChevronUp size={16} /> : <FiChevronDown size={16} />}
        </Flex>
      </Button>

      <Collapsible.Root open={isOpen || isPolling}>
        <Collapsible.Content>
          <Box
            mt={4}
            p={6}
            borderRadius="xl"
            bg="linear-gradient(to left, rgb(95, 77, 215), rgb(154, 110, 243))"
            border="2px solid rgba(255, 255, 255, 0.1)"
          >
            {/* Loading/Polling State */}
            {(isLoading || isPolling) && (
              <Box mb={6}>
                <Flex align="center" gap={3} mb={4}>
                  <Spinner size="md" color="white" />
                  <Text color="white" fontSize="md" fontWeight="medium">
                    {isPolling ? 'Processing video clips...' : 'Starting download job...'}
                  </Text>
                </Flex>
                
                {isPolling && pollProgress.total > 0 && (
                  <Box>
                    <Flex justify="space-between" mb={2}>
                      <Text color="white" fontSize="sm">
                        Progress: {pollProgress.current} / {pollProgress.total} clips
                      </Text>
                      <Text color="white" fontSize="sm" fontWeight="bold">
                        {pollProgress.percent}%
                      </Text>
                    </Flex>
                    <Progress.Root value={pollProgress.percent}>
                      <Progress.Track bg="rgba(255, 255, 255, 0.2)" borderRadius="full" height="12px">
                        <Progress.Range bg="rgb(76, 136, 233)" />
                      </Progress.Track>
                    </Progress.Root>
                    {pollProgress.failed > 0 && (
                      <Text color="yellow.300" fontSize="xs" mt={2}>
                        {pollProgress.failed} clips failed
                      </Text>
                    )}
                  </Box>
                )}
              </Box>
            )}

            {/* Error Message */}
            {error && !isPolling && (
              <Box
                mb={4}
                p={4}
                borderRadius="lg"
                bg="rgba(255, 0, 0, 0.2)"
                border="1px solid rgba(255, 0, 0, 0.4)"
              >
                <Text color="white" fontSize="md" fontWeight="medium">
                  {error}
                </Text>
              </Box>
            )}

            {/* Overall Sentiment Section - only show if no error and we have data */}
            {!error && keyMoments.length > 0 && !isPolling && (
              <Box 
                borderRadius="lg" 
                py={4} 
                opacity={0.9} 
                boxShadow="0 0 10px 0 rgba(0, 0, 0, 0.1)" 
                p={5} 
                border="2px solid rgb(226, 220, 220)" 
                bg="linear-gradient(to left, rgb(117, 132, 226),rgb(165, 130, 236))"
                mb={6}
              >
                <Flex align="center" gap={2} pb={2}>
                  <FiTrendingUp size={18} color="white" />
                  <Text color="white" fontSize="md" fontWeight="medium">
                    Overall Sentiment
                  </Text>
                </Flex>
                
                <Flex align="center" gap={4} mb={3} color="rgb(39, 46, 151)">
                  <Icon size={48}/>
                  <Box>
                    <Text fontSize="2xl" fontWeight="bold">
                      {score}/100
                    </Text>
                    <Text color="white" fontSize="md">
                      {label}
                    </Text>
                  </Box>
                </Flex>
                
                <Progress.Root value={score}>
                  <Progress.Track bg="purple.300" borderRadius="full" height="8px">
                    <Progress.Range bg="rgb(31, 40, 159)" />
                  </Progress.Track>
                </Progress.Root>
              </Box>
            )}

            {/* Key Moments Section */}
            {keyMoments.length > 0 && !isPolling && (
              <>
                <Text color="white" fontSize="lg" fontWeight="semibold" mb={4}>
                  Key Moments ({keyMoments.length})
                </Text>

                <Grid
                  templateColumns={{ base: '1fr', md: 'repeat(2, 1fr)', lg: 'repeat(3, 1fr)' }}
                  gap={4}
                >
                  {keyMoments.map((moment) => (
                    <Box
                      key={moment.id}
                      borderRadius="lg"
                      overflow="hidden"
                      bg="rgba(255, 255, 255, 0.1)"
                      border="1px solid rgba(255, 255, 255, 0.2)"
                      transition="all 0.3s"
                      _hover={{
                        transform: 'translateY(-4px)',
                        boxShadow: '0 10px 20px rgba(0, 0, 0, 0.3)',
                        borderColor: 'rgba(255, 255, 255, 0.4)',
                      }}
                    >
                      <Box position="relative">
                        <Image
                          src={moment.thumbnail}
                          alt={moment.title}
                          width="100%"
                          height="180px"
                          objectFit="cover"
                        />
                        <Box
                          position="absolute"
                          top={2}
                          right={2}
                          bg="rgba(0, 0, 0, 0.7)"
                          color="white"
                          px={2}
                          py={1}
                          borderRadius="md"
                          fontSize="xs"
                          fontWeight="medium"
                        >
                          {moment.duration}
                        </Box>
                        <Box
                          position="absolute"
                          bottom={2}
                          left={2}
                          bg="rgba(0, 0, 0, 0.7)"
                          color="white"
                          px={2}
                          py={1}
                          borderRadius="md"
                          fontSize="xs"
                          fontWeight="medium"
                        >
                          {moment.timestamp}
                        </Box>
                      </Box>

                      <Box p={4}>
                        <Text color="white" fontSize="md" fontWeight="semibold" mb={3}>
                          {moment.title}
                        </Text>
                        <Button
                          onClick={() => handleDownload(moment.clipUrl, moment.title)}
                          width="100%"
                          background="linear-gradient(to right, rgb(117, 132, 226), rgb(165, 130, 236))"
                          color="white"
                          borderRadius="md"
                          size="sm"
                          _hover={{
                            background: 'linear-gradient(to left, rgb(117, 132, 226), rgb(165, 130, 236))',
                          }}
                        >
                          <Flex align="center" gap={2}>
                            <FiDownload size={16} />
                            Download
                          </Flex>
                        </Button>
                      </Box>
                    </Box>
                  ))}
                </Grid>
              </>
            )}
          </Box>
        </Collapsible.Content>
      </Collapsible.Root>
    </Box>
  )
}

export default KeyMoments
