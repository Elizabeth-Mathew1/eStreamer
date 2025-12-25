import { Box, Text, Flex } from '@chakra-ui/react'
import { useSelector } from 'react-redux'

const HotTopics = () => {
  const analyticsData = useSelector((state) => state.stream.analyticsData)
  const topTopics = analyticsData?.top_topics || []

  if (topTopics.length === 0) {
    return null
  }

  return (
    <Box
      bg="linear-gradient(to right, rgb(59, 130, 246), rgb(139, 92, 246))"
      borderRadius="xl"
      p={4}
      pb={6}
      mb={6}
      mt={8}
    >
      <Flex align="center" gap={2} mb={4}>
        <Text fontSize="30px">🔥</Text>
        <Text color="white" fontSize="lg" fontWeight="semibold">
          Hot Topics
        </Text>
        <Text color="white" fontSize="sm" opacity={0.9}>
          ({topTopics.length})
        </Text>
      </Flex>

      <Flex gap={6} wrap="wrap">
        {topTopics.map((topic, index) => (
          <Box
            key={index}
            bg="linear-gradient(to right, rgb(236, 72, 153), rgb(219, 39, 119))"
            borderRadius="full"
            px={4}
            py={2}
          >
            <Text color="white" fontSize="16px" fontWeight="medium">
              #{topic}
            </Text>
          </Box>
        ))}
      </Flex>
    </Box>
  )
}

export default HotTopics

