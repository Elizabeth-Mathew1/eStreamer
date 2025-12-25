import { Box, Text, Flex } from '@chakra-ui/react'
import { useSelector } from 'react-redux'
import { IoChatbubbleOutline, IoPersonOutline } from 'react-icons/io5'

const TopChats = () => {
  const analyticsData = useSelector((state) => state.stream.analyticsData)
  const topChats = analyticsData?.top_chats || []

  const parsedChats = topChats.map((chatObj) => {
    const user = Object.keys(chatObj)[0]
    return { user, message: chatObj[user] }
  })
  
  if (parsedChats.length === 0) {
    return null
  }

  return (
    <Box
      bg="gray.800"
      borderRadius="xl"
      p={6}
      mb={6}
      border="1px solid"
      borderColor="gray.700"
      flex={1}
      display="flex"
      flexDirection="column"
      height="100%"
      overflow="hidden"
    >
      <Flex align="center" justify="space-between" mb={4} flexShrink={0}>
        <Flex align="center" gap={2}>
          <IoChatbubbleOutline size={20} color="white" />
          <Text color="white" fontSize="lg" fontWeight="semibold">
            Top Chats
          </Text>
        </Flex>
        <Text color="gray.400" fontSize="sm">
          ({parsedChats.length})
        </Text>
      </Flex>

      <Box flex={1} overflowY="auto" overflowX="hidden" pr={2} minH={0}>
        <Flex direction="column" gap={3}>
          {parsedChats.map((chat, index) => (
            <Box
              key={index}
              bg="gray.700"
              borderRadius="lg"
              p={4}
              border="1px solid"
              borderColor="gray.600"
            >
              <Flex align="center" gap={2} mb={2}>
                <IoPersonOutline size={18} color="white" />
                <Text color="white" fontSize="sm" fontWeight="medium">
                  {chat.user}
                </Text>
              </Flex>
              <Text color="gray.300" fontSize="sm">
                {chat.message}
              </Text>
            </Box>
          ))}
        </Flex>
      </Box>
    </Box>
  )
}

export default TopChats

