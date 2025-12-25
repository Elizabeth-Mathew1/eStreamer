import { Box, Text, Flex, Progress } from '@chakra-ui/react'
import { useSelector } from 'react-redux'
import { IoVideocamOutline } from 'react-icons/io5'
import { FiTrendingUp } from 'react-icons/fi'
import { 
  IoHappy, 
  IoSad 
} from 'react-icons/io5'
import { RiEmotionNormalFill } from 'react-icons/ri'
import { TIME_RANGES, LOADING_STATUS } from '../common'         

const getSentimentInfo = (avgSentiment) => {
  // Convert -1 to 1 range to 0-100
  const score = Math.round(((avgSentiment + 1) / 2) * 100)
  
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

const SentimentBox = () => {
  const analyticsData = useSelector((state) => state.stream.analyticsData)
  const duration = useSelector((state) => state.stream.duration)
  const videoUrl = useSelector((state) => state.stream.videoUrl)
  
  const avgSentiment = analyticsData?.avg_sentiment ?? 0
  const { score, label, Icon } = getSentimentInfo(avgSentiment)
  
  console.log(avgSentiment)

  const timeLabel = TIME_RANGES.find((range) => range.seconds === duration)?.label || 'Last 60 minutes'
  
  // Get current date/time
  const now = new Date()
  const dateStr = now.toLocaleDateString('en-GB', { day: '2-digit', month: '2-digit', year: 'numeric' })
  const timeStr = now.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  
  // Extract video title from URL (simplified - you might want to fetch actual title)
  const videoTitle = "Join 2819 Church LIVE! // Sundays @8:00a EST" //TODO

  return (
    <Box
      bg="linear-gradient(to left, rgb(95, 77, 215),rgb(154, 110, 243))"
      borderRadius="xl"
      p={6}
      mb={6}
      mt={8}
    >
      {/* Top Section: Live Stream Info */}
      <Flex align="center" gap={2} mb={2} flexWrap="wrap">
        <IoVideocamOutline size={18} color="white" />
        <Text color="white" fontSize="sm">
          {dateStr}, {timeStr}
        </Text>
        <Text color="white" fontSize="sm">•</Text>
        <Text color="white" fontSize="sm">{timeLabel}</Text>
      </Flex>
      <Text color="white" fontSize="18px" fontWeight="semibold" mb={4}>
        Live Stream: {videoTitle}
      </Text>

      {/* Bottom Section: Overall Sentiment */}
        <Box borderRadius="lg" py={4} opacity={0.9} boxShadow="0 0 10px 0 rgba(0, 0, 0, 0.1)" p={5} border="2px solid rgb(226, 220, 220)" bg="linear-gradient(to left, rgb(117, 132, 226),rgb(165, 130, 236))">
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
    </Box>
  )
}

export default SentimentBox

