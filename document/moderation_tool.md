# Building a Moderation tool

## Intro

Dailymotion is building a backend tool to track the moderation actions made on the uploaded
videos and you're the software architect.

The frontend team has already built a slick moderation UI (the "Moderation Console UI"),
they now need the backend server to connect to.

The API is splited in two services: the Moderation Queue and the Dailymotion API Proxy.
You


## Your task

The task is to create both services: the Moderation Queue and the Dailymotion API Proxy.

<details>
<summary>
When a new video is uploaded on Dailymotion, a server-to-server POST request is sent to your Moderation Queue web service with the video id:
</summary>

```bash
$ curl -XPOST $MODERATION_QUEUE_SERVER/add_video -d '{ "video_id": 123456 }'
<< HTTP 201
```
</details>

<details>
<summary>
When a moderator connects to the Moderation console UI, the UI will fetch the next **PENDING** video to moderate with.
</summary>

Notice for each request, UI will append a `Authorization` header with moderator name encoded in base64.

```bash
# base64 encode of "john.doe" is "am9obi5kb2U="
$ curl -XGET $MODERATION_QUEUE_SERVER/get_video --header 'Authorization: am9obi5kb2U='
<< HTTP 200
{
  "video_id": 123456
}
```

Also notice video in Moderation Queue is ordered by First-In-First-Out, same moderator will get same video when repeat call this endpoint. different moderator should get different video when call this endpoint.
</details>

<details>
<summary>
Then the Moderation Console UI will query your "Dailymotion API Proxy" with the returned video_id
to retrieve all the information required to show the video to the moderator.
</summary>


And your "Dailymotion API Proxy" will query the Dailymotion API (https://developer.dailymotion.com/api)
and acts as a proxy. For this specific test, for any video requested your service can just returns
the information for this video: http://www.dailymotion.com/video/x2m8jpp
eg.

```bash
$ curl -XGET $DAILYMOTION_API_PROXY/get_video_info/123456
<< HTTP 200
{
  "title": "Dailymotion Spirit Movie",
  "channel": "creation",
  "owner": ...,
  "filmstrip_60_url": ...,
  "embed_url": ...
}
```

Notice: for this test, all video id ends with 404 (404, 1404, 10404, ...) are consider as not exists (HTTP 404)
</details>

<details>
<summary>
Once the moderator has viewed the video, he should takes action and flags the **PENDING** video as "spam" or "not spam".
</summary>

```bash
$ curl -XPOST $MODERATION_QUEUE_SERVER/flag_video -d '{ "video_id" : 123456, "status": "not spam" }  --header 'Authorization: am9obi5kb2U='
<< HTTP 200
{
  "video_id": 123456,
  "status": "not spam"
}
```
</details>


<details>
<summary>
Also, we need to expose a endpoint for administrator to monitoring service status. this endpoint will return the number of videos in the queue and number of videos flagged as spam and not spam.
</summary>

```bash
$ curl -XGET $MODERATION_QUEUE_SERVER/stats
<< HTTP 200
{
  "total_pending_videos": ...,
  "total_spam_videos": ...,
  "total_not_spam_videos": ...
}
```
</details>


<details>
<summary>
Finally, we need to expose a endpoint to review video moderation history for audit purpose.
</summary>

```bash
$ curl -XGET $MODERATION_QUEUE_SERVER/log_video/123456
<< HTTP 200
[
  {"date": "2000-01-01 12:00:00", "status": "pending", "moderator": null },
  {"date": "2000-01-01 13:00:00", "status": "spam", "moderator": "john.doe"}
]
```
</details>

## Summary

```
                              Moderation Console UI (nothing to build)
                               /           \
                             /               \
                           /                   \
              Moderation console API         Dailymotion API Proxy
                * add_video                    * get_video_info
                * get_video
                * flag_video
                * stats
                * log_video
```


The Moderation Console API must support the following use cases:
  - Add a new uploaded video
  - Get the next video to moderate
  - Update a video status (spam or not spam)
  - Multiple moderators must be able to work at the same time, they should always work on different videos.
  - Monitoring queue status
  - View moderation history of a video
  - The service should be restartable without losing any data

The Dailymotion API Proxy should implement a caching system and handle nicely API errors


## What do we expect

* PHP or Python languages are supported. Choose the one that you master the most.
* We expect to have a level of code quality which could go to production.
* Using frameworks is allowed only for routing, dependency injection, event dispatcher, db connection. Don't use magic (ORM for example)! We want to see your implementation.
* Use the DBMS you want (except SQLite).
* Your code should be tested.
* Your application has to run within a docker containers.
* You can use AI to help you, but in a smart way. However, please make iterative commits as we analyze them to understand your development reasoning (not all the code in 1 or 2 commits).
* You should provide us the link to GitHub.
* You should provide us the instructions to run your code and your tests. We should not install anything except docker/docker-compose to run you project.
* You should provide us an architecture schema.
