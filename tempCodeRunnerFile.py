# Test allowed requests
# for i in range(4):
#     try:
#         with RateLimitContext(limiter, key) as result:
#             print(f"Request {i+1}: allowed, remaining={result.remaining}")
#     except RateLimitExceeded as e:
#         print(f"Request {i+1}: DENIED — {e}")

# # Test reset_on_exit
# print("\nTesting reset_on_exit:")
# with RateLimitContext(limiter, key, reset_on_exit=True) as result:
#     print(f"After reset attempt: remaining={result.remaining}")