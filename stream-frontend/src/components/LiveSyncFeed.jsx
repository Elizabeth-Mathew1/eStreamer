import React, { useState, useEffect } from 'react'
import { Box, Text, Flex, Progress } from '@chakra-ui/react'
import { useSelector } from 'react-redux'
import { useLazyGetCorrelationQuery } from '../features/api/apiSlice'
import { IoMicOutline, IoChatbubbleOutline, IoRadioButtonOn } from 'react-icons/io5'
import { FiTrendingUp, FiTrendingDown } from 'react-icons/fi'
import { RiEmotionNormalFill } from 'react-icons/ri'

// Extract video ID from YouTube URL
const extractVideoId = (url) => {
  if (!url) return null
  const match = url.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&\n?#]+)/)
  return match ? match[1] : null
}

// Calculate sync strength (0-100) based on volume and users
const calculateSyncStrength = (volume, users) => {
  if (!volume || !users) return 0
  // Simple formula: normalize based on volume/users ratio
  // Higher volume and more users = higher sync strength
  const ratio = (volume / Math.max(users, 1)) * users
  return Math.min(Math.round((ratio / 500) * 100), 100)
}

// Get sentiment info
const getSentimentInfo = (sentiment) => {
  if (sentiment > 0) {
    return { label: 'Positive', color: 'green', Icon: FiTrendingUp }
  } else if (sentiment < 0) {
    return { label: 'Negative', color: 'red', Icon: FiTrendingDown }
  } else {
    return { label: 'Neutral', color: 'gray', Icon: RiEmotionNormalFill }
  }
}

// Get emojis based on sentiment
const getEmojis = (sentiment) => {
  if (sentiment > 0) {
    return ['🔥', '😱', '👏']
  } else if (sentiment < 0) {
    return ['🤡', '📉', '💀']
  } else {
    return ['😐', '➖', '⚪']
  }
}

// Format time to HH:MM:SS
const formatTime = (date) => {
  return date.toLocaleTimeString('en-GB', { 
    hour: '2-digit', 
    minute: '2-digit', 
    second: '2-digit' 
  })
}

const LiveSyncFeed = () => {
  const videoUrl = useSelector((state) => state.stream.videoUrl)
  const videoId = extractVideoId(videoUrl)
  
  const [correlationEvents, setCorrelationEvents] = useState([])
  const [selectedEventIndex, setSelectedEventIndex] = useState(null)
  const [triggerCorrelation] = useLazyGetCorrelationQuery()

  // Poll every 5 seconds
  useEffect(() => {
    if (!videoId) return

    const pollCorrelation = async () => {
      try {
        const result = await triggerCorrelation(videoId).unwrap()
        
        // Create new event with timestamp
        const newEvent = {
          timestamp: new Date(),
          ...result,
        }
        
        // Add to events list (keep last 50 events)
        setCorrelationEvents((prev) => {
          const updated = [newEvent, ...prev]
          return updated.slice(0, 50)
        })
      } catch (error) {
        console.error('Error fetching correlation:', error)
      }
    }

    // Poll immediately, then every 5 seconds
    pollCorrelation()
    const interval = setInterval(pollCorrelation, 80000)

    return () => clearInterval(interval)
  }, [videoId, triggerCorrelation])

  if (!videoId || correlationEvents.length === 0) {
    return null
  }

  const selectedEvent = selectedEventIndex !== null 
    ? correlationEvents[selectedEventIndex] 
    : null

  const selectedChats = selectedEvent?.correlated_chat_data?.correlated_chats || []

  return (
    <Box mb={6} mt={8}>
      <Flex align="center" gap={2} mb={4}>
        <Box
          style={{
            filter: 'drop-shadow(0 0 8px rgba(154, 110, 243, 0.8))',
            animation: 'livePulse 2s ease-in-out infinite',
          }}
        >
          <IoRadioButtonOn size={24} color="rgb(154, 110, 243)" />
        </Box>
        <Text color="white" fontSize="20px" fontWeight="semibold">
          Live Sync Feed
        </Text>
      </Flex>
      
      <Flex gap={6} align="stretch" height="600px">
        {/* Left Panel: Sync Events */}
        <Box
          flex={1}
          bg="gray.800"
          borderRadius="xl"
          p={4}
          border="1px solid"
          borderColor="gray.700"
          display="flex"
          flexDirection="column"
          overflow="hidden"
        >
          <Box flex={1} overflowY="auto" pr={2}>
            <Flex direction="column" gap={4}>
              {correlationEvents.map((event, index) => {
                const syncStrength = calculateSyncStrength(
                  event.correlated_chat_data?.correlated_chat_volume || 0,
                  event.correlated_chat_data?.correlated_users || 0
                )
                const sentimentInfo = getSentimentInfo(event.audio_data?.audio_sentiment || 0)
                const emojis = getEmojis(event.audio_data?.audio_sentiment || 0)
                
                return (
                  <Box
                    key={index}
                    bg={selectedEventIndex === index ? "gray.700" : "gray.900"}
                    borderRadius="lg"
                    p={4}
                    border="1px solid"
                    borderColor={selectedEventIndex === index ? "purple.400" : "gray.600"}
                    cursor="pointer"
                    onClick={() => setSelectedEventIndex(index)}
                    _hover={{
                      borderColor: "purple.400",
                      bg: "gray.700",
                    }}
                  >
                    {/* Timestamp */}
                    <Flex align="center" gap={2} mb={2}>
                      <Box w="8px" h="8px" borderRadius="full" bg="blue.300" />
                      <Text color="blue.300" fontSize="sm">
                        {formatTime(event.timestamp)}
                      </Text>
                    </Flex>

                    {/* Event Name */}
                    <Flex align="center" gap={2} mb={3}>
                      <IoMicOutline size={40} color="white" />
                      <Text color="white" fontSize="16px">
                        {event.audio_data?.audio_summary || 'No summary'}
                      </Text>
                    </Flex>

                    {/* Sync Strength */}
                      <Text color="gray.400" fontSize="xs" mb={1}>
                        SYNC STRENGTH
                      </Text>
                      <Progress.Root value={syncStrength}>
                        <Progress.Track bg="gray.700" borderRadius="full" height="6px">
                          <Progress.Range bg="purple.400" />
                        </Progress.Track>
                      </Progress.Root>
                      <Text color="purple.300" fontSize="xs" mt={1}>
                        {syncStrength}%
                      </Text>

                    {/* Metrics */}
                    <Flex gap={4} mb={3} mt={2}>
                      <Box
                        bg="linear-gradient(to left, rgb(95, 77, 215),rgb(154, 110, 243))"
                        borderRadius="lg"
                        p={3}
                        flex={1}
                      >
                        <Text color="white" fontSize="sm" fontWeight="medium" mb={1}>
                          Correlated Chat Volume
                        </Text>
                        <Text color="white" fontSize="lg" fontWeight="bold">
                          {event.correlated_chat_data?.correlated_chat_volume || 0}
                        </Text>
                      </Box>
                      <Box
                        bg="linear-gradient(to left, rgb(95, 77, 215),rgb(154, 110, 243))"
                        borderRadius="lg"
                        p={3}
                        flex={1}
                      >
                        <Text color="white" fontSize="sm" fontWeight="medium" mb={1}>
                          Correlated Audience
                        </Text>
                        <Text color="white" fontSize="lg" fontWeight="bold">
                          {event.correlated_chat_data?.correlated_users || 0}
                        </Text>
                      </Box>
                    </Flex>

                    {/* Emojis */}
                    <Flex mb={3} gap={2}>
                      {emojis.map((emoji, i) => (
                        <Text key={i} fontSize="lg">
                          {emoji}
                        </Text>
                      ))}
                    </Flex>

                    {/* Sentiment Badge */}
                    <Box
                      bg={sentimentInfo.color === 'green' ? 'green.500' : sentimentInfo.color === 'red' ? 'red.500' : 'gray.500'}
                      px={3}
                      py={1}
                      borderRadius="md"
                      display="inline-flex"
                      alignItems="center"
                      gap={2}
                      mt={4}
                    >
                      {sentimentInfo.color === 'green' ? (
                        <FiTrendingUp size={16} color="white" />
                      ) : sentimentInfo.color === 'red' ? (
                        <FiTrendingDown size={16} color="white" />
                      ) : (
                        <RiEmotionNormalFill size={16} color="white" />
                      )}
                      <Text color="white" fontSize="14px" fontWeight="medium">
                        {sentimentInfo.label}
                      </Text>
                    </Box>
                  </Box>
                )
              })}
            </Flex>
          </Box>
        </Box>

        {/* Right Panel: Correlated Messages */}
        <Box
          flex={1}
          bg="gray.800"
          borderRadius="xl"
          p={4}
          border="1px solid"
          borderColor="gray.700"
          display="flex"
          flexDirection="column"
          overflow="hidden"
        >
          <Flex align="center" gap={2} mb={4} flexShrink={0}>
            <IoChatbubbleOutline size={20} color="white" />
            <Text color="white" fontSize="lg" fontWeight="semibold">
              Correlated Messages
            </Text>
          </Flex>

          <Box flex={1} overflowY="auto" pr={2}>
            {selectedChats.length === 0 ? (
              <Text color="gray.400" fontSize="sm" textAlign="center" mt={8}>
                {selectedEventIndex === null 
                  ? 'Click an event to view correlated messages' 
                  : 'Don\'t worry, if you don\'t see any messages, it means the streamer is not talking about anything that the viewers are talking about :)'}
              </Text>
            ) : (
              <Flex direction="column" gap={3}>
                {selectedChats.map((chat, index) => {
                  // Parse chat object with schema: { message: string, sender: string }
                  const sender = chat?.sender || 'Unknown'
                  const message = chat?.message || ''

                  return (
                    <Box
                      key={index}
                      bg="gray.700"
                      borderRadius="lg"
                      p={3}
                      border="1px solid"
                      borderColor="gray.600"
                    >
                      <Flex align="center" gap={2} justify="space-between">
                        <Box flex={1}>
                          <Text color="blue.300" fontSize="sm" fontWeight="medium" mb={1}>
                            {sender}
                          </Text>
                          <Text color="white" fontSize="sm">
                            {message}
                          </Text>
                        </Box>
                      </Flex>
                    </Box>
                  )
                })}
              </Flex>
            )}
          </Box>
        </Box>
      </Flex>
    </Box>
  )
}

export default LiveSyncFeed

