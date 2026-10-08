import 'package:flutter/material.dart';
import 'package:workout_app/services/user_analytics_service.dart';

class AmplitudeTestScreen extends StatefulWidget {
  const AmplitudeTestScreen({Key? key}) : super(key: key);

  @override
  State<AmplitudeTestScreen> createState() => _AmplitudeTestScreenState();
}

class _AmplitudeTestScreenState extends State<AmplitudeTestScreen> {
  bool _isSending = false;
  String _lastStatus = '';

  Future<void> _sendTestEvent() async {
    setState(() {
      _isSending = true;
      _lastStatus = 'Sending test event...';
    });

    try {
      await UserAnalyticsService.instance.trackTestEvent();
      setState(() {
        _lastStatus = '✅ Test event sent successfully!';
      });
    } catch (e) {
      setState(() {
        _lastStatus = '❌ Failed to send test event: $e';
      });
    } finally {
      setState(() {
        _isSending = false;
      });
    }
  }

  Future<void> _sendCustomEvent() async {
    setState(() {
      _isSending = true;
      _lastStatus = 'Sending custom event...';
    });

    try {
      await UserAnalyticsService.instance.trackUserAction('custom_test_event', properties: {
        'button_clicked': 'custom_button',
        'screen': 'amplitude_test_screen',
        'user_action': 'testing_custom_event',
        'timestamp': DateTime.now().toIso8601String(),
      });
      setState(() {
        _lastStatus = '✅ Custom event sent successfully!';
      });
    } catch (e) {
      setState(() {
        _lastStatus = '❌ Failed to send custom event: $e';
      });
    } finally {
      setState(() {
        _isSending = false;
      });
    }
  }

  Future<void> _testFunnelEvents() async {
    setState(() {
      _isSending = true;
      _lastStatus = 'Testing funnel events...';
    });

    try {
      // Test Step 1: Profile Published
      await UserAnalyticsService.instance.trackTrainerProfilePublished(properties: {
        'has_tagline': true,
        'has_description': true,
        'has_specializations': true,
        'profile_completion_score': 0.8,
      });

      // Wait a bit between events
      await Future.delayed(const Duration(milliseconds: 500));

      // Test Step 2: Inbound Request
      await UserAnalyticsService.instance.trackInboundRequestReceived(
        requestId: 'test_req_123',
        clientUserId: 'test_client_456',
        properties: {
          'request_type': 'booking',
          'client_level': 'beginner',
        },
      );

      await Future.delayed(const Duration(milliseconds: 500));

      // Test Step 3: Booking Accepted
      await UserAnalyticsService.instance.trackBookingAccepted(
        bookingId: 'test_booking_789',
        clientUserId: 'test_client_456',
        properties: {
          'booking_type': 'personal_training',
          'session_count': 1,
        },
      );

      await Future.delayed(const Duration(milliseconds: 500));

      // Test Step 4: Payout Received (First Dollar!)
      await UserAnalyticsService.instance.trackPayoutReceived(
        payoutId: 'test_payout_abc',
        amount: 99.99,
        currency: 'USD',
        properties: {
          'commission_amount': 9.99,
          'net_amount': 90.00,
          'time_to_first_payout_days': 7,
        },
      );

      setState(() {
        _lastStatus = '✅ Funnel events sent successfully!\n\n🎯 Time-to-First-Dollar funnel:\n1. Profile Published ✅\n2. Inbound Request ✅\n3. Booking Accepted ✅\n4. Payout Received ✅';
      });
    } catch (e) {
      setState(() {
        _lastStatus = '❌ Failed to send funnel events: $e';
      });
    } finally {
      setState(() {
        _isSending = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Amplitude Test'),
      ),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Icon(
              Icons.analytics,
              size: 80,
              color: Colors.blue,
            ),
            const SizedBox(height: 24),
            const Text(
              'Amplitude Analytics Test',
              style: TextStyle(
                fontSize: 24,
                fontWeight: FontWeight.bold,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 16),
            const Text(
              'Test your Amplitude integration by sending events to analytics.',
              style: TextStyle(fontSize: 16),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 32),
            ElevatedButton(
              onPressed: _isSending ? null : _sendTestEvent,
              style: ElevatedButton.styleFrom(
                padding: const EdgeInsets.all(16),
                backgroundColor: Colors.blue,
                foregroundColor: Colors.white,
              ),
              child: _isSending
                  ? const CircularProgressIndicator(color: Colors.white)
                  : const Text(
                      'Send Test Event',
                      style: TextStyle(fontSize: 16),
                    ),
            ),
            const SizedBox(height: 16),
            ElevatedButton.icon(
              onPressed: _isSending ? null : _sendCustomEvent,
              icon: const Icon(Icons.analytics_outlined),
              label: const Text('Send Custom Event'),
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.green,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
              ),
            ),
            const SizedBox(height: 16),
            ElevatedButton.icon(
              onPressed: () {
                UserAnalyticsService.instance.debugInfo();
                setState(() {
                  _lastStatus = '🔍 Debug info logged to console';
                });
              },
              icon: const Icon(Icons.bug_report_outlined),
              label: const Text('Show Debug Info'),
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.orange,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
              ),
            ),
            const SizedBox(height: 16),
            ElevatedButton.icon(
              onPressed: _isSending ? null : _testFunnelEvents,
              icon: const Icon(Icons.trending_up),
              label: const Text('Test Time-to-First-Dollar Funnel'),
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.purple,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
              ),
            ),
            const SizedBox(height: 24),
            if (_lastStatus.isNotEmpty)
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: _lastStatus.contains('✅') 
                      ? Colors.green.withOpacity(0.1)
                      : Colors.red.withOpacity(0.1),
                  border: Border.all(
                    color: _lastStatus.contains('✅') 
                        ? Colors.green
                        : Colors.red,
                  ),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  _lastStatus,
                  style: TextStyle(
                    fontSize: 14,
                    color: _lastStatus.contains('✅') 
                        ? Colors.green.shade700
                        : Colors.red.shade700,
                  ),
                  textAlign: TextAlign.center,
                ),
              ),
          ],
        ),
      ),
    );
  }
}
