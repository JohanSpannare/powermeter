# powermeter


## Create table
CREATE TABLE `Log` (
  `Logtime` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `Rate` smallint(6) NOT NULL,
  `Duration` decimal(6,4) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4