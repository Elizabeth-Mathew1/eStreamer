import grpc
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import proto.stream_list_pb2 as stream_list_pb2
import proto.stream_list_pb2_grpc as stream_list_pb2_grpc

REST_API_KEY = ###
OAUTH_TOKEN = ###

def get_live_chat_id_rest() -> str | None:
    """Uses the REST API to find the Live Chat ID from the Video ID."""
    video_id = "lFnZPGwGttc"
    print(f"\n--- STEP 1: REST - Finding Chat ID for Video {video_id} ---")
    try:
        youtube_rest = build("youtube", "v3", developerKey=REST_API_KEY)
        
        response = youtube_rest.videos().list(
            part="liveStreamingDetails",
            id=video_id
        ).execute()

        if not response.get('items'): 
            return None

        live_chat_id = response['items'][0].get('liveStreamingDetails', {}).get('activeLiveChatId')
        
        if live_chat_id:
            print(f"SUCCESS: Retrieved Live Chat ID: {live_chat_id}")
        return live_chat_id

    except HttpError as e:
        print(f"REST API Error: {e}")
        return None


def youtube_ingest():

    next_page_token = None
    live_chat_id = get_live_chat_id_rest()


    metadata = (('authorization', f'Bearer {OAUTH_TOKEN}'),)
    creds = grpc.ssl_channel_credentials()
    


    with grpc.secure_channel("dns:///youtube.googleapis.com:443", creds) as channel:
        stub = stream_list_pb2_grpc.V3DataLiveChatMessageServiceStub(channel)
       
        while True:
            try:
                print(f"\n--- Requesting chat stream for: {live_chat_id}. Next token: {next_page_token or 'None'} ---")
            
            # Build the request message using the generated Protobuf class
                request = stream_list_pb2.LiveChatMessageListRequest(
                part=["snippet", "authorDetails"], 
                live_chat_id=live_chat_id,
                max_results=200,
                page_token=next_page_token,
            )   
            
                # The StreamList call returns an iterable stream of responses (Server Streaming RPC)
                for response in stub.StreamList(request, metadata=metadata):
                    for item in response.items:
                        author = item.author_details.display_name
                        message = item.snippet.display_message
                        print(f"[{author}]: {message}")
                        # Update the token for the next stream iteration or a reconnection
                        next_page_token = response.next_page_token
                        if not next_page_token:
                            print("Stream ended or encountered terminal message.")
                            break
            
            except grpc.RpcError as e:
                # Check if the error is due to a natural close (EOF/stream end) or an issue
                print(f"\n--- gRPC Error: {e.code()} - {e.details()} ---")

                if e.code() == grpc.StatusCode.UNAUTHENTICATED:
                    print("Authentication failed. Check if your OAuth token is expired or invalid.")
                    break 

                elif e.code() == grpc.StatusCode.UNAVAILABLE or e.code() == grpc.StatusCode.INTERNAL:
                    print("Connection issue. Attempting reconnect in 5 seconds...")
                    time.sleep(5)
                    continue

                else:
                    break


            except KeyboardInterrupt:
                print("\n--- Streaming stopped by user. ---")
                break


if __name__ == "__main__":
    youtube_ingest()


