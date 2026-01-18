/*
 * lwIP Options Configuration for CYW43 WiFi
 */

#ifndef LWIPOPTS_H
#define LWIPOPTS_H

/* FreeRTOS integration (NO_SYS=0 means use RTOS) */
#define NO_SYS                          0
#define LWIP_SOCKET                     0

/* Thread safety for FreeRTOS */
#define SYS_LIGHTWEIGHT_PROT            1
#define LWIP_TCPIP_CORE_LOCKING         1
#define LWIP_TCPIP_CORE_LOCKING_INPUT   1

/* FreeRTOS mailbox sizes (required when NO_SYS=0) */
#define TCPIP_MBOX_SIZE                 8
#define DEFAULT_RAW_RECVMBOX_SIZE       8
#define DEFAULT_UDP_RECVMBOX_SIZE       8
#define DEFAULT_TCP_RECVMBOX_SIZE       8
#define DEFAULT_ACCEPTMBOX_SIZE         8

/* FreeRTOS thread stack sizes */
#define TCPIP_THREAD_STACKSIZE          1024
#define TCPIP_THREAD_PRIO               (configMAX_PRIORITIES - 2)

/* Memory configuration */
#define MEM_LIBC_MALLOC                 0
#define MEM_ALIGNMENT                   4
#define MEM_SIZE                        4000
#define MEMP_NUM_TCP_SEG                32
#define MEMP_NUM_ARP_QUEUE              10
#define PBUF_POOL_SIZE                  24

/* Core protocols */
#define LWIP_ARP                        1
#define LWIP_ETHERNET                   1
#define LWIP_ICMP                       1
#define LWIP_RAW                        1
#define LWIP_IPV4                       1
#define LWIP_TCP                        1
#define LWIP_UDP                        1
#define LWIP_DNS                        1
#define LWIP_DHCP                       1

/* TCP tuning */
#define TCP_WND                         (8 * TCP_MSS)
#define TCP_MSS                         1460
#define TCP_SND_BUF                     (8 * TCP_MSS)
#define TCP_SND_QUEUELEN                ((4 * (TCP_SND_BUF) + (TCP_MSS - 1)) / (TCP_MSS))
#define LWIP_TCP_KEEPALIVE              1

/* Callbacks */
#define LWIP_NETIF_STATUS_CALLBACK      1
#define LWIP_NETIF_LINK_CALLBACK        1
#define LWIP_NETIF_HOSTNAME             1
#define LWIP_NETIF_TX_SINGLE_PBUF       1

/* No netconn/socket API needed */
#define LWIP_NETCONN                    0

/* DHCP */
#define DHCP_DOES_ARP_CHECK             0
#define LWIP_DHCP_DOES_ACD_CHECK        0

/* Checksum */
#define LWIP_CHKSUM_ALGORITHM           3

/* Statistics (disabled for size) */
#define MEM_STATS                       0
#define SYS_STATS                       0
#define MEMP_STATS                      0
#define LINK_STATS                      0

/* Debug (disabled for release) */
#define LWIP_DEBUG                      0

#endif /* LWIPOPTS_H */
