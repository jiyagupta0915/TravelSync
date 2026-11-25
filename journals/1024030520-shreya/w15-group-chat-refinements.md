# Week 15 : Project Report, Group Chat Refinements and Chat Assistant

## Work done

+  Prepared the complete end-semester project report with the help of
   my teammates, in LaTeX on the official TIET report template.
   +  Updated the content from the mid-semester report to match the
      final implementation, and added the team's UML diagrams, data
      flow diagrams and screenshots of the application.
   +  Ran the test suites and measured response times, throughput and
      recommendation accuracy for the Results and Evaluation chapter.
+  Group chat:
   +  live message delivery over WebSockets;
   +  loading older messages;
   +  deleting messages;
   +  destination suggestions shown as cards in the chat, with
      destination details;
   +  unread message counts and read receipts.
+  Added sharing a recommended destination with a group directly from
   the destination finder.
+  Completed the TravelSync chat assistant: a floating chat widget that
   answers questions about places, packing, health, trips and groups,
   with an optional AI model used only when it cannot answer itself.
+  Wrote backend and frontend tests for these features.

## Problem faced and how I solved it

+  **Problem:** chat messages from other members appeared only through
   polling every few seconds, so the chat felt slow.
+  **Solution:** added a WebSocket connection per group. After a message
   is saved, the server pushes it to every member who has the group
   open. Polling stays as a fallback in case the connection drops.