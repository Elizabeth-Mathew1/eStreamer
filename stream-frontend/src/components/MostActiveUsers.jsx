import { Box, Text, Flex } from '@chakra-ui/react'
import { useSelector } from 'react-redux'
import { IoPeopleOutline, IoChatbubbleOutline } from 'react-icons/io5'

const MostActiveUsers = () => {
  const analyticsData = useSelector((state) => state.stream.analyticsData)
  const topUsers = analyticsData?.top_users || []

  const parsedUsers = topUsers.map((userObj) => {
    const user = Object.keys(userObj)[0]
    return { user, messages: userObj[user] }
  })

  if (parsedUsers.length === 0) {
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
      <Flex align="center" gap={2} mb={4} flexShrink={0}>
        <IoPeopleOutline size={20} color="white" />
        <Text color="white" fontSize="lg" fontWeight="semibold">
          Most Active Users
        </Text>
      </Flex>

      <Box flex={1} display="flex" flexDirection="column" overflow="hidden" minH={0}>
        <Flex justify="space-between" mb={2} pb={2} borderBottom="1px solid" borderColor="gray.600" flexShrink={0}>
          <Text color="gray.400" fontSize="sm" fontWeight="medium" w="60px">Rank</Text>
          <Text color="gray.400" fontSize="sm" fontWeight="medium" flex={1}>Username</Text>
          <Text color="gray.400" fontSize="sm" fontWeight="medium" w="100px">Messages</Text>
        </Flex>

        <Box flex={1} overflowY="auto" overflowX="hidden" pr={2} minH={0}>
          <Flex direction="column" gap={2}>
          {parsedUsers.map((user, index) => (
            <Flex key={index} justify="space-between" align="center" py={2}>
              <Box
                w="32px"
                h="32px"
                borderRadius="full"
                bg="blue.300"
                display="flex"
                alignItems="center"
                justifyContent="center"
              >
                <Text color="white" fontSize="sm" fontWeight="bold">
                  {index + 1}
                </Text>
              </Box>
              <Text color="white" fontSize="sm" flex={1} ml={6}>
                {user.user}
              </Text>
              <Flex align="center" gap={1} w="100px" justify="flex-end" pr={12}>
                <IoChatbubbleOutline size={14} color="white" />
                <Text color="white" fontSize="sm">
                  {user.messages}
                </Text>
              </Flex>
            </Flex>
          ))}
          </Flex>
        </Box>
      </Box>
    </Box>
  )
}

export default MostActiveUsers

