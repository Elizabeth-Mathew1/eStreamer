// src/components/PredictiveAnalysis.jsx
import { useState, useEffect } from 'react'
import { Box, Text, Flex, Spinner } from '@chakra-ui/react'
import { FiZap, FiTrendingUp, FiTrendingDown } from 'react-icons/fi'
import { useSelector } from 'react-redux'
import { useGetPredictionMutation } from '../features/api/apiSlice'
import { LOADING_STATUS } from '../common'

// Extract video ID from YouTube URL
const extractVideoId = (url) => {
  if (!url) return null
  const match = url.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&\n?#]+)/)
  return match ? match[1] : null
}

// Convert sentiment score (-1 to 1) to 0-100 scale
const sentimentToScore = (sentiment) => {
  if (sentiment === null || sentiment === undefined) return 50
  return Math.round(((sentiment + 1) / 2) * 100)
}

// Get color gradient based on sentiment
const getSentimentGradient = (sentiment) => {
  const score = sentimentToScore(sentiment)
  
  if (score >= 70) {
    // Positive - Green gradient
    return 'linear-gradient(to right, rgb(34, 197, 94), rgb(22, 163, 74))'
  } else if (score >= 50) {
    // Neutral-Positive - Yellow/Orange gradient
    return 'linear-gradient(to right, rgb(251, 191, 36), rgb(245, 158, 11))'
  } else if (score >= 30) {
    // Neutral-Negative - Orange gradient
    return 'linear-gradient(to right, rgb(249, 115, 22), rgb(234, 88, 12))'
  } else {
    // Negative - Red gradient
    return 'linear-gradient(to right, rgb(239, 68, 68), rgb(220, 38, 38))'
  }
}

// Get sentiment label
const getSentimentLabel = (sentiment) => {
  const score = sentimentToScore(sentiment)
  
  if (score >= 80) {
    return 'Highly Positive'
  } else if (score >= 60) {
    return 'Positive'
  } else if (score >= 50) {
    return 'Stable'
  } else if (score >= 40) {
    return 'Declining'
  } else {
    return 'Negative'
  }
}

// Get strategy icon
const getStrategyIcon = (strategy) => {
  if (!strategy) return FiZap
  const lowerStrategy = strategy.toLowerCase()
  if (lowerStrategy.includes('maintain') || lowerStrategy.includes('keep')) {
    return FiTrendingUp
  } else if (lowerStrategy.includes('change') || lowerStrategy.includes('shift')) {
    return FiTrendingDown
  } else {
    return FiZap
  }
}

const PredictiveAnalysis = () => {
  const [prediction, setPrediction] = useState(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)
  
  const videoUrl = useSelector((state) => state.stream.videoUrl)
  const isAnalyzing = useSelector((state) => state.stream.isAnalyzing)
  const [getPrediction] = useGetPredictionMutation()

  // Fetch prediction when analysis is successful (triggered by Analyze button)
  useEffect(() => {
    const fetchPrediction = async () => {
      // Only fetch when analysis is successful
      if (isAnalyzing !== LOADING_STATUS.SUCCESS) {
        setPrediction(null)
        setError(null)
        return
      }

      const videoId = extractVideoId(videoUrl)
      if (!videoId) {
        console.warn('No video ID found for prediction')
        return
      }

      setIsLoading(true)
      setError(null)
      
      try {
        console.log('Fetching prediction for video ID:', videoId)
        const result = await getPrediction(videoId).unwrap()
        console.log('Prediction result:', result)
        
        // Validate result data
        if (!result) {
          setError('No prediction data received')
          setPrediction(null)
          return
        }
        
        // Check if required fields exist
        if (
          result.sentiment_score === null || 
          result.sentiment_score === undefined ||
          result.strategy === null ||
          result.strategy === undefined ||
          result.reasoning === null ||
          result.reasoning === undefined
        ) {
          setError('Incomplete prediction data received')
          setPrediction(null)
          return
        }
        
        setPrediction(result)
      } catch (err) {
        console.error('Error fetching prediction:', err)
        setError(err?.data?.error || err?.data?.message || 'Failed to fetch prediction')
        setPrediction(null)
      } finally {
        setIsLoading(false)
      }
    }

    // Add a small delay to ensure analytics are ready
    const timer = setTimeout(() => {
      fetchPrediction()
    }, 2500) // Slightly after analytics fetch (which happens at 2000ms)

    return () => clearTimeout(timer)
  }, [videoUrl, isAnalyzing, getPrediction])

  // Don't show anything if analysis hasn't started or is loading
  if (isAnalyzing !== LOADING_STATUS.SUCCESS) {
    return null
  }

  if (isLoading) {
    return (
      <Box
        bg="linear-gradient(to right, rgb(251, 191, 36), rgb(245, 158, 11))"
        borderRadius="xl"
        p={6}
        mb={6}
        mt={6}
      >
        <Flex align="center" gap={3}>
          <Spinner size="md" color="white" />
          <Text color="white" fontSize="md" fontWeight="medium">
            Analyzing predictions...
          </Text>
        </Flex>
      </Box>
    )
  }

  if (error) {
    // Show error message instead of hiding
    return (
      <Box
        bg="linear-gradient(to right, rgb(239, 68, 68), rgb(220, 38, 38))"
        borderRadius="xl"
        p={6}
        mb={6}
        mt={6}
      >
        <Text color="white" fontSize="md" fontWeight="medium">
          Prediction Error: {error}
        </Text>
      </Box>
    )
  }

  if (!prediction) {
    return null // Don't show anything if no prediction yet
  }

  // Additional null checks before rendering
  const sentimentScore = sentimentToScore(prediction.sentiment_score ?? 0)
  const gradient = getSentimentGradient(prediction.sentiment_score ?? 0)
  const label = getSentimentLabel(prediction.sentiment_score ?? 0)
  const StrategyIcon = getStrategyIcon(prediction.strategy)
  const strategy = prediction.strategy || 'No strategy available'
  const reasoning = prediction.reasoning || 'No reasoning available'

  return (
    <Box
      bg={gradient}
      borderRadius="xl"
      p={6}
      mb={6}
      mt={6}
      boxShadow="0 4px 6px rgba(0, 0, 0, 0.1)"
    >
      <Flex align="center" gap={2} mb={4}>
        <StrategyIcon size={24} color="white" />
        <Text color="white" fontSize="20px" fontWeight="semibold">
          Predictive Analytics
        </Text>
      </Flex>

      <Flex direction={{ base: 'column', md: 'row' }} gap={6} align="stretch">
        {/* Left Side - Recommended Action */}
        <Box flex={1} display="flex" flexDirection="column">
          <Flex align="center" gap={2} mb={2}>
            
            <Text color="white" fontSize="sm" fontWeight="medium" textTransform="uppercase">
              Recommended Action
            </Text>
          </Flex>
          <Box 
            border="1px solid rgba(255, 255, 255, 0.3)" 
            borderRadius="xl" 
            p={2}
            flex={1}
            display="flex"
            alignItems="center"
          >
            <Text color="white" fontSize="18px" fontWeight="semibold">
              {strategy}
            </Text>
          </Box>
        </Box>

        {/* Right Side - Predicted Sentiment */}
        <Box flex={1} display="flex" flexDirection="column">
          <Text color="white" fontSize="sm" fontWeight="medium" mb={2} textTransform="uppercase">
            Predicted Sentiment
          </Text>
          <Box 
            border="1px solid rgba(255, 255, 255, 0.3)" 
            borderRadius="xl" 
            p={2}
            flex={1}
            display="flex"
            flexDirection="column"
            justifyContent="center"
          >
            <Flex align="baseline" gap={2} mb={1}>
              <Text color="white" fontSize="20px" fontWeight="semibold">
                {sentimentScore} / 100
              </Text>
            </Flex>
            <Text color="white" fontSize="md" fontWeight="medium">
              {label}
            </Text>
          </Box>
        </Box>
      </Flex>

      {/* Why This Strategy Section */}
      <Box
        mt={4}
        pt={4}
        borderTop="1px solid rgba(255, 255, 255, 0.3)"
      >
        <Text color="white" fontSize="sm" fontWeight="semibold" mb={2}>
          Why This Strategy?
        </Text>
        <Text color="white" fontSize="sm" opacity={0.95} lineHeight="1.6">
          {reasoning}
        </Text>
      </Box>
    </Box>
  )
}

export default PredictiveAnalysis