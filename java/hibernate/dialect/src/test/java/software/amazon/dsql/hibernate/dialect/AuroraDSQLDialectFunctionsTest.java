// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0 OR LGPL-2.1
package software.amazon.dsql.hibernate.dialect;

import org.hibernate.query.sqm.TemporalUnit;
import org.hibernate.sql.ast.spi.SqlAppender;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.Mock;
import org.mockito.MockitoAnnotations;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.LocalTime;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.Calendar;
import java.util.Date;
import java.util.TimeZone;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.Mockito.*;

/**
 * Unit tests for the SQL function and formatting capabilities of {@link AuroraDSQLDialect}.
 */
public class AuroraDSQLDialectFunctionsTest {

    private AuroraDSQLDialect dialect;

    @Mock
    private SqlAppender appender;

    @BeforeEach
    public void setUp() {
        MockitoAnnotations.openMocks(this);
        dialect = new AuroraDSQLDialect();
    }

    @Test
    public void testAppendBooleanValueString() {
        dialect.appendBooleanValueString(appender, true);
        verify(appender).appendSql(true);

        dialect.appendBooleanValueString(appender, false);
        verify(appender).appendSql(false);
    }

    @Test
    public void testExtractPattern() {
        // Test day of week adjustment (PostgreSQL returns 0-6, dialect adjusts to 1-7)
        String dayOfWeekPattern = dialect.extractPattern(TemporalUnit.DAY_OF_WEEK);
        assertEquals("(extract(?1 from ?2)+1)", dayOfWeekPattern);

        // Test other temporal units remain unchanged
        String dayPattern = dialect.extractPattern(TemporalUnit.DAY);
        assertEquals("extract(?1 from ?2)", dayPattern);
    }

    @Test
    public void testTimestampaddPattern() {
        String pattern = dialect.timestampaddPattern(TemporalUnit.DAY, jakarta.persistence.TemporalType.TIMESTAMP, null);
        assertEquals("cast(?3+(?2)*interval '1 day' as timestamp)", pattern);

        pattern = dialect.timestampaddPattern(TemporalUnit.QUARTER, jakarta.persistence.TemporalType.DATE, null);
        assertEquals("cast(?3+(?2)*interval '3 month' as date)", pattern);
    }

    @Test
    public void testTimestampdiffPattern() {
        String pattern = dialect.timestampdiffPattern(
                TemporalUnit.DAY, 
                jakarta.persistence.TemporalType.DATE, 
                jakarta.persistence.TemporalType.DATE);
        assertEquals("(?3-?2)", pattern);

        pattern = dialect.timestampdiffPattern(
                TemporalUnit.MONTH, 
                jakarta.persistence.TemporalType.TIMESTAMP, 
                jakarta.persistence.TemporalType.TIMESTAMP);
        assertEquals("(extract(year from ?3-?2)*12+extract(month from ?3-?2))", pattern);
    }

    @Test
    public void testAppendDateTimeLiteral_TemporalAccessor() {
        LocalDate date = LocalDate.of(2023, 5, 15);
        dialect.appendDateTimeLiteral(appender, date, jakarta.persistence.TemporalType.DATE, TimeZone.getDefault());
        verify(appender).appendSql("date '");
        verify(appender).appendSql('\'');

        reset(appender);

        LocalTime time = LocalTime.of(14, 30, 45);
        dialect.appendDateTimeLiteral(appender, time, jakarta.persistence.TemporalType.TIME, TimeZone.getDefault());
        verify(appender).appendSql("time '");
        verify(appender).appendSql('\'');

        reset(appender);

        OffsetDateTime timestamp = OffsetDateTime.of(
                LocalDateTime.of(2023, 5, 15, 14, 30, 45), 
                ZoneOffset.UTC);
        dialect.appendDateTimeLiteral(appender, timestamp, jakarta.persistence.TemporalType.TIMESTAMP, TimeZone.getDefault());
        verify(appender).appendSql("timestamp with time zone '");
        verify(appender).appendSql('\'');
    }

    @Test
    public void testAppendDateTimeLiteral_Date() {
        Date date = new Date();
        
        dialect.appendDateTimeLiteral(appender, date, jakarta.persistence.TemporalType.DATE, TimeZone.getDefault());
        verify(appender).appendSql("date '");
        verify(appender).appendSql('\'');

        reset(appender);

        dialect.appendDateTimeLiteral(appender, date, jakarta.persistence.TemporalType.TIME, TimeZone.getDefault());
        verify(appender).appendSql("time with time zone '");
        verify(appender).appendSql('\'');

        reset(appender);

        dialect.appendDateTimeLiteral(appender, date, jakarta.persistence.TemporalType.TIMESTAMP, TimeZone.getDefault());
        verify(appender).appendSql("timestamp with time zone '");
        verify(appender).appendSql('\'');
    }

    @Test
    public void testAppendDateTimeLiteral_Calendar() {
        Calendar calendar = Calendar.getInstance();
        
        dialect.appendDateTimeLiteral(appender, calendar, jakarta.persistence.TemporalType.DATE, TimeZone.getDefault());
        verify(appender).appendSql("date '");
        verify(appender).appendSql('\'');

        reset(appender);

        dialect.appendDateTimeLiteral(appender, calendar, jakarta.persistence.TemporalType.TIME, TimeZone.getDefault());
        verify(appender).appendSql("time with time zone '");
        verify(appender).appendSql('\'');

        reset(appender);

        dialect.appendDateTimeLiteral(appender, calendar, jakarta.persistence.TemporalType.TIMESTAMP, TimeZone.getDefault());
        verify(appender).appendSql("timestamp with time zone '");
        verify(appender).appendSql('\'');
    }

    @Test
    public void testDatetimeFormat() {
        assertEquals("YYYY-MM-DD", dialect.datetimeFormat("yyyy-MM-dd").result());
        assertEquals("HH24:MI:SS", dialect.datetimeFormat("HH:mm:ss").result());
        assertEquals("YYYY-MM-DD HH24:MI:SS.MS", dialect.datetimeFormat("yyyy-MM-dd HH:mm:ss.SSS").result());
    }
}
