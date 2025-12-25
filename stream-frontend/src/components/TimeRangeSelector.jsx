import React from 'react'
import { useSelector, useDispatch } from 'react-redux'
import { Box, Button, Flex, Text } from '@chakra-ui/react'
import { IoTimeOutline } from 'react-icons/io5'
import { setDuration } from '../features/stream/streamSlice'
import { TIME_RANGES } from '../common'


const TimeRangeSelector = () => {
  const dispatch = useDispatch()
  const selectedDuration = useSelector((state) => state.stream.duration)

  return (
    <Box mt={8}>
      <Flex align="center" gap={2} mb={4} color="blue.300">
        <IoTimeOutline size={26} />
        <Text color="white" fontSize="16px" fontWeight="semibold">
          Time Range
        </Text>
      </Flex>

      <Flex gap={4} wrap="wrap">
        {TIME_RANGES.map(({ label, seconds }, index) => (
          <Button
            key={seconds}   
            onClick={() => dispatch(setDuration(seconds))}
            background={
              selectedDuration === seconds
                ? 'linear-gradient(to right, rgb(42, 20, 183), #9f7aea)'
                : 'transparent'
            }
            color="white"
            border={selectedDuration === seconds ? 'none' : '2px solid'}
            borderColor={selectedDuration === seconds ? 'transparent' : 'gray.600'}
            borderRadius="lg"
            px={6}
            py={2}
            height="48px"
            fontSize="14px"
            fontWeight="medium"
            _hover={{
              borderColor: selectedDuration === seconds ? 'transparent' : 'gray.500',
            }}
          >
            {label}
          </Button>
        ))}
      </Flex>
      
    </Box>
  )
}

export default TimeRangeSelector

