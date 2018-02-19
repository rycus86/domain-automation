# Domain automation

[![Build Status](https://travis-ci.org/rycus86/domain-automation.svg?branch=master)](https://travis-ci.org/rycus86/domain-automation)
[![Docker Stars](https://img.shields.io/docker/stars/rycus86/domain-automation.svg)](https://hub.docker.com/r/rycus86/domain-automation/)
[![Coverage Status](https://coveralls.io/repos/github/rycus86/domain-automation/badge.svg?branch=master)](https://coveralls.io/github/rycus86/domain-automation?branch=master)
[![Code Climate](https://codeclimate.com/github/rycus86/domain-automation/badges/gpa.svg)](https://codeclimate.com/github/rycus86/domain-automation)

Python app to help automate dynamic DNS and SSL certificate updates
with notifications and signals.

## Design

The application is designed to execute two steps for each managed subdomains
in a sequence, repeated on a schedule:

1. Check and adjust DNS records
2. Check and update SSL certificates

Notifications are sent for each DNS record and SSL update.
The DNS maintenance is mainly for servers on dynamic IP addresses, 
e.g. the public IP address is not fixed, and it needs updating every time it changes.
The public IP address is fetched once per run, and it is used for every subdomain
within the same run.

The application defines [factories](https://github.com/rycus86/domain-automation/blob/master/src/factories.py)
to create manager instances for each component:

- [scheduler](https://github.com/rycus86/domain-automation/tree/master/src/scheduler) for the scheduling logic (start, cancel, etc.)
- [notification](https://github.com/rycus86/domain-automation/tree/master/src/notifications) for sending notifications on updates
- [discovery](https://github.com/rycus86/domain-automation/tree/master/src/discovery) to collect the list of managed subdomains
- [dns manager](https://github.com/rycus86/domain-automation/tree/master/src/dns_manager) to get the public IP address, the current IP address for DNS records of subdomains, and to update them if needed
- [ssl manager](https://github.com/rycus86/domain-automation/tree/master/src/ssl_manager) to fetch or renew SSL certificates when needed

Notification managers are composable to process updates sequentially,
each of them for every notification.
Every other manager has one configured instance.

Every component uses a *noop* implementation by default.
This can be overridden with configuration, coming from a configuration file
or environment variables.

For example, a configuration called `COMPONENT_CONFIG` would be look up in:

1. A specific key-value file, if it contains a line with `COMPONENT_CONFIG=...`
2. The default key-value file at `/var/secrets/app.config` for fallback
3. The `COMPONENT_CONFIG` environment variable if not found in the files
4. The default value specified in the component

*Note:* `bool` values generally accept the `yes`, `true`, `1` values to make them true,
ignoring the character case.

## Component implementations

The application currently supports the following implementations for its managers.

### Schedulers

The scheduler instance to use can be configured using the `SCHEDULER_CLASS` key.
The value should be full module plus class name, for example
`scheduler.oneshot.OneShotScheduler` for the default implementation.
In this example, the `OneShotScheduler` class is defined in the `oneshot` module,
under the `scheduler` module ([see it here](https://github.com/rycus86/domain-automation/blob/master/src/scheduler/oneshot.py)).

#### One-shot scheduler

`SCHEDULER_CLASS=scheduler.oneshot.OneShotScheduler`

This is the default scheduler used.
It executes the update once, and it does not repeat.
This means the application executes one update, then exits.

#### Five minutes scheduler

`SCHEDULER_CLASS=scheduler.repeat.FiveMinutesScheduler`

After an update, the next run is scheduled to start 5 minutes after the previous one
has finished.
By default, the first run will start after 5 minutes the application has started.

| Configuration item | Configuration key | Configuration file | Default value | Required |
| ------------------ | ----------------- | ------------------ | ------------- | -------- |
| Start the first execution as soon as the application starts | `IMMEDIATE_START` | `/var/secrets/app.config` | `no` | no |

#### Docker aware scheduled

`SCHEDULER_CLASS=scheduler.repeat_docker.DockerAwareScheduler`

Based on the *five minutes scheduler* above, it also connects to the Docker API on the host,
and listens for *Swarm service create events*, to kick off an out-of-schedule update.

| Configuration item | Configuration key | Configuration file | Default value | Required |
| ------------------ | ----------------- | ------------------ | ------------- | -------- |
| Start the first execution as soon as the application starts | `IMMEDIATE_START` | `/var/secrets/app.config` | `no` | no |

### Notifications

Notification managers are configured with the `NOTIFICATION_MANAGER_CLASS` key.
To include more than one notification manager, use a comma separated value for each of their
full package plus class name (without whitespace), for example:

```
NOTIFICATION_MANAGER_CLASS=notifications.log_notification.LoggingNotificationManager,notifications.slack_message.SlackNotificationManager
```

The default `notifications.noop.NoopNotificationManager` will not execute or log anything.

#### Log notification manager

`NOTIFICATION_MANAGER_CLASS=notifications.log_notification.LoggingNotificationManager`

Logs messages to the standard output or error streams, depending on whether the update
has been successful or not.

#### Slack notification manager

`NOTIFICATION_MANAGER_CLASS=notifications.slack_message.SlackNotificationManager`

Sends updates and messages to a [Slack](https://slack.com/) channel, using a [chatbot](https://api.slack.com/bot-users).

| Configuration item | Configuration key | Configuration file | Default value | Required |
| ------------------ | ----------------- | ------------------ | ------------- | -------- |
| Slack API token | `SLACK_TOKEN` | `/var/secrets/notifications` | none | yes |
| Slack channel | `SLACK_CHANNEL` | `/var/secrets/notifications` | `general` | no |
| Name of the Slack bot | `SLACK_BOT_NAME` | `/var/secrets/notifications` | `domain-automation-bot` | no |
| The URL of the Slack bot's avatar image | `SLACK_BOT_ICON` | `/var/secrets/notifications` | none | no |

#### Docker signal notification manager

`NOTIFICATION_MANAGER_CLASS=notifications.docker_signal.DockerSignalNotification`

Sends Docker signals (using `docker kill` to containers with the specified label.
The value of the label is the signal to send, for example: `domain.automation.signal=HUP`
would send a `SIGHUP` signal to the main process (`pid 1`) in the container.

| Configuration item | Configuration key | Configuration file | Default value | Required |
| ------------------ | ----------------- | ------------------ | ------------- | -------- |
| The Docker __container__ label name | `DOCKER_SIGNAL_LABEL` | `/var/secrets/notifications` | domain.automation.signal | no |

This manager uses __container__ labels (not Swarm service labels), but it does support
Swarm services and stacks.
The actual signal in Swarm is sent through a temporary global service, see a bit more details
[in my blog post](https://blog.viktoradam.net/2018/02/17/auto-dns-and-ssl-management/).

### Discovery

The discovery manager instance can be configured using the `DISCOVERY_CLASS` key.
Its purpose is to provide the list of subdomains the application manages.

#### Docker labels discovery

`DISCOVERY_CLASS=discovery.docker_labels.DockerLabelsDiscovery`

This implementation uses Docker labels (*either* service or container labels)
to collect the subdomains.

| Configuration item | Configuration key | Configuration file | Default value | Required |
| ------------------ | ----------------- | ------------------ | ------------- | -------- |
| Name of the Docker label | `DOCKER_DISCOVERY_LABEL` | `/var/secrets/discovery` | `discovery.domain.name` | no |
| The default *root* domain | `DEFAULT_DOMAIN` | `/var/secrets/app.config` | `localhost.local` | no |

Multiple subdomains may be given on a single label value, separated by the `,` comma character.

### DNS managers

DNS managers are responsible for keeping DNS records pointing to *dynamic IP addresses*
up to date.
The implementation to use is configured using the `DNS_MANAGER_CLASS` configuration key.

#### Cloudflare DNS manager

`DNS_MANAGER_CLASS=dns_manager.cloudflare_dns.CloudflareDNSManager`

This manager manager DNS records through [Cloudflare](https://www.cloudflare.com/) `A` records with *IPv4* addresses.
The implentation needs configuration for using the [Cloudflare API](https://api.cloudflare.com/) with the
registered email address and the token that belongs to it.
To fetch the current public IP address, [api.ipify.org](https://www.ipify.org) is used.

| Configuration item | Configuration key | Configuration file | Default value | Required |
| ------------------ | ----------------- | ------------------ | ------------- | -------- |
| The registered email address in Cloudflare | `CLOUDFLARE_EMAIL` | `/var/secrets/cloudflare` | none | yes |
| The Cloudflare API access token | `CLOUDFLARE_TOKEN` | `/var/secrets/cloudflare` | none | yes |

### SSL managers

SSL managers fetch and renew SSL certificates.
The implementation is chosen by the `SSL_MANAGER_CLASS` configuration.

#### Certbot using Cloudflare DNS authenticator

`SSL_MANAGER_CLASS=ssl_manager.certbot_cf_ssl.CertbotCloudflareSSLManager`

This implementation uses [certbot](https://github.com/certbot/certbot) to 
get new and renewed SSL certificates from [Let's Encrypt](https://letsencrypt.org/).
The domain verification is done through *TXT* DNS records in Cloudflare using
the [Cloudflare DNS Authenticator plugin](https://github.com/certbot/certbot/tree/master/certbot-dns-cloudflare).

| Configuration item | Configuration key | Configuration file | Default value | Required |
| ------------------ | ----------------- | ------------------ | ------------- | -------- |
| The registered email address in Cloudflare | `CLOUDFLARE_EMAIL` | `/var/secrets/cloudflare` | none | yes |
| The Cloudflare API access token | `CLOUDFLARE_TOKEN` | `/var/secrets/cloudflare` | none | yes |
| Allowed DNS propagation time (in seconds) to wait before the domain verification starts | `DNS_PROPAGATION_SECONDS` | `/var/secrets/certbot` | `30` | no |
| Timeout for the `certbot` command execution (in seconds) | `CERTBOT_TIMEOUT` | `/var/secrets/certbot` | `120` | no |
| Use staging *ACME* servers for testing | `CERTBOT_STAGING` | `/var/secrets/certbot` | `no` | no |

## Usage

The application is written for Python 3 but *should* work with Python 2.7 as well.

Having the configuration in place, either through configuration files or
environment variables or a mix of them, the app can be started with:

```shell
$ python app.py
```

To install any missing dependencies, run:

```shell
$ pip install -r requirements.txt
```

The application is also available as a [Docker image](https://hub.docker.com/r/rycus86/domain-automation/).
To run it:

```shell
$ docker run -d --name domain-automation            \
    -v /var/run/docker.sock:/var/run/docker.sock    \
    -e SETTING_TO_OVERRIDE=abcd                     \
    -v $PWD/config.file:/var/secrets/app.config     \
    rycus86/domain-automation
```

The `/var/run/docker.sock` mount is only required for managers using the Docker API.
The Docker image supports the `amd64`, `armv7` and `arm64v8` platforms.

The same container above as a Compose service:

```yaml
version: '2'
services:

  automation:
    image: rycus86/domain-automation
    environment:
      - SETTING_TO_OVERRIDE=abcd
    volumes:
      - $PWD/config.file:/var/secrets/app.config
      - /var/run/docker.sock:/var/run/docker.sock
```

Again, the same, using Swarm services and secrets:

```yaml
version: '3.5'
services:

  automation:
    image: rycus86/domain-automation
    deploy:
      replicas: 1
      placement:
        constraints:
          - node.role == manager
    environment:
      - SETTING_TO_OVERRIDE=abcd
    secrets:
      - source: app-config
        target: /var/secrets/app.config
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock

secrets:
  app-config:
    file: ./config.file
    name: app-config-v${VERSION}
```

More information and explanation can be found on my blog
[in the related post](https://blog.viktoradam.net/2018/02/17/auto-dns-and-ssl-management/).

## License

MIT
