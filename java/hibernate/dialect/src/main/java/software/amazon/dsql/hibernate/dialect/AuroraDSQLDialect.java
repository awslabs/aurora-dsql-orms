// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0 OR LGPL-2.1
package software.amazon.dsql.hibernate.dialect;

import static java.sql.Types.FLOAT;
import static org.hibernate.query.sqm.TemporalUnit.DAY;
import static org.hibernate.query.sqm.TemporalUnit.EPOCH;
import static org.hibernate.type.SqlTypes.BINARY;
import static org.hibernate.type.SqlTypes.BLOB;
import static org.hibernate.type.SqlTypes.CHAR;
import static org.hibernate.type.SqlTypes.CLOB;
import static org.hibernate.type.SqlTypes.GEOGRAPHY;
import static org.hibernate.type.SqlTypes.GEOMETRY;
import static org.hibernate.type.SqlTypes.INET;
import static org.hibernate.type.SqlTypes.JSON;
import static org.hibernate.type.SqlTypes.LONG32NVARCHAR;
import static org.hibernate.type.SqlTypes.LONG32VARBINARY;
import static org.hibernate.type.SqlTypes.LONG32VARCHAR;
import static org.hibernate.type.SqlTypes.NCHAR;
import static org.hibernate.type.SqlTypes.NCLOB;
import static org.hibernate.type.SqlTypes.NVARCHAR;
import static org.hibernate.type.SqlTypes.OTHER;
import static org.hibernate.type.SqlTypes.SQLXML;
import static org.hibernate.type.SqlTypes.TIME;
import static org.hibernate.type.SqlTypes.TIMESTAMP;
import static org.hibernate.type.SqlTypes.TIMESTAMP_UTC;
import static org.hibernate.type.SqlTypes.TIMESTAMP_WITH_TIMEZONE;
import static org.hibernate.type.SqlTypes.TIME_UTC;
import static org.hibernate.type.SqlTypes.TINYINT;
import static org.hibernate.type.SqlTypes.UUID;
import static org.hibernate.type.SqlTypes.VARBINARY;
import static org.hibernate.type.SqlTypes.VARCHAR;
import static org.hibernate.type.descriptor.DateTimeUtils.appendAsDate;
import static org.hibernate.type.descriptor.DateTimeUtils.appendAsTime;
import static org.hibernate.type.descriptor.DateTimeUtils.appendAsTimestampWithMicros;
import static org.hibernate.type.descriptor.DateTimeUtils.appendAsTimestampWithMillis;

import jakarta.persistence.TemporalType;
import java.sql.CallableStatement;
import java.sql.DatabaseMetaData;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Types;
import java.time.temporal.ChronoField;
import java.time.temporal.TemporalAccessor;
import java.util.Calendar;
import java.util.Date;
import java.util.TimeZone;
import java.util.UUID;
import org.hibernate.LockMode;
import org.hibernate.LockOptions;
import org.hibernate.StaleObjectStateException;
import org.hibernate.boot.Metadata;
import org.hibernate.boot.model.FunctionContributions;
import org.hibernate.boot.model.TypeContributions;
import org.hibernate.boot.model.relational.SqlStringGenerationContext;
import org.hibernate.dialect.Dialect;
import org.hibernate.dialect.DmlTargetColumnQualifierSupport;
import org.hibernate.dialect.NationalizationSupport;
import org.hibernate.dialect.OracleDialect;
import org.hibernate.dialect.PgJdbcHelper;
import org.hibernate.dialect.PostgreSQLCastingInetJdbcType;
import org.hibernate.dialect.PostgreSQLCastingIntervalSecondJdbcType;
import org.hibernate.dialect.PostgreSQLCastingJsonJdbcType;
import org.hibernate.dialect.PostgreSQLSqlAstTranslator;
import org.hibernate.dialect.PostgreSQLStructCastingJdbcType;
import org.hibernate.dialect.Replacer;
import org.hibernate.dialect.SelectItemReferenceStrategy;
import org.hibernate.dialect.TimeZoneSupport;
import org.hibernate.dialect.aggregate.AggregateSupport;
import org.hibernate.dialect.aggregate.PostgreSQLAggregateSupport;
import org.hibernate.dialect.function.CommonFunctionFactory;
import org.hibernate.dialect.function.PostgreSQLMinMaxFunction;
import org.hibernate.dialect.function.PostgreSQLTruncFunction;
import org.hibernate.dialect.function.PostgreSQLTruncRoundFunction;
import org.hibernate.dialect.lock.LockingStrategy;
import org.hibernate.dialect.lock.LockingStrategyException;
import org.hibernate.dialect.lock.PessimisticWriteSelectLockingStrategy;
import org.hibernate.dialect.pagination.LimitHandler;
import org.hibernate.dialect.pagination.OffsetFetchLimitHandler;
import org.hibernate.dialect.unique.CreateTableUniqueDelegate;
import org.hibernate.dialect.unique.UniqueDelegate;
import org.hibernate.engine.jdbc.dialect.spi.DialectResolutionInfo;
import org.hibernate.engine.jdbc.env.spi.NameQualifierSupport;
import org.hibernate.engine.spi.SessionFactoryImplementor;
import org.hibernate.event.spi.EventSource;
import org.hibernate.mapping.ForeignKey;
import org.hibernate.metamodel.mapping.EntityMappingType;
import org.hibernate.metamodel.spi.RuntimeModelCreationContext;
import org.hibernate.persister.entity.Lockable;
import org.hibernate.query.SemanticException;
import org.hibernate.query.sqm.CastType;
import org.hibernate.query.sqm.FetchClauseType;
import org.hibernate.query.sqm.IntervalType;
import org.hibernate.query.sqm.TemporalUnit;
import org.hibernate.query.sqm.mutation.internal.cte.CteInsertStrategy;
import org.hibernate.query.sqm.mutation.internal.cte.CteMutationStrategy;
import org.hibernate.query.sqm.mutation.spi.SqmMultiTableInsertStrategy;
import org.hibernate.query.sqm.mutation.spi.SqmMultiTableMutationStrategy;
import org.hibernate.query.sqm.produce.function.StandardFunctionArgumentTypeResolvers;
import org.hibernate.service.ServiceRegistry;
import org.hibernate.sql.ast.SqlAstTranslator;
import org.hibernate.sql.ast.SqlAstTranslatorFactory;
import org.hibernate.sql.ast.spi.SqlAppender;
import org.hibernate.sql.ast.spi.StandardSqlAstTranslatorFactory;
import org.hibernate.sql.ast.tree.Statement;
import org.hibernate.sql.exec.spi.JdbcOperation;
import org.hibernate.tool.schema.internal.StandardForeignKeyExporter;
import org.hibernate.tool.schema.spi.Exporter;
import org.hibernate.type.JavaObjectType;
import org.hibernate.type.descriptor.ValueBinder;
import org.hibernate.type.descriptor.WrapperOptions;
import org.hibernate.type.descriptor.java.JavaType;
import org.hibernate.type.descriptor.java.PrimitiveByteArrayJavaType;
import org.hibernate.type.descriptor.jdbc.BasicBinder;
import org.hibernate.type.descriptor.jdbc.BlobJdbcType;
import org.hibernate.type.descriptor.jdbc.ClobJdbcType;
import org.hibernate.type.descriptor.jdbc.JdbcType;
import org.hibernate.type.descriptor.jdbc.ObjectNullAsBinaryTypeJdbcType;
import org.hibernate.type.descriptor.jdbc.UUIDJdbcType;
import org.hibernate.type.descriptor.jdbc.XmlJdbcType;
import org.hibernate.type.descriptor.jdbc.spi.JdbcTypeRegistry;
import org.hibernate.type.descriptor.sql.internal.CapacityDependentDdlType;
import org.hibernate.type.descriptor.sql.internal.DdlTypeImpl;
import org.hibernate.type.descriptor.sql.internal.Scale6IntervalSecondDdlType;
import org.hibernate.type.descriptor.sql.spi.DdlTypeRegistry;
import org.hibernate.type.spi.TypeConfiguration;

public class AuroraDSQLDialect extends Dialect {

  public AuroraDSQLDialect() {
    super();
  }

  public AuroraDSQLDialect(DialectResolutionInfo dialectResolutionInfo) {
    super(dialectResolutionInfo);
  }

  private final Exporter<ForeignKey> NO_FK_SUPPORT_EXPORTER =
      new StandardForeignKeyExporter(this) {
        @Override
        public String[] getSqlCreateStrings(
            ForeignKey foreignKey, Metadata metadata, SqlStringGenerationContext context) {
          // Foreign key constraints are unsupported
          return NO_COMMANDS;
        }
      };

  private static final LockingStrategy NO_LOCKING_STRATEGY =
      new LockingStrategy() {
        @Override
        public void lock(Object o, Object o1, Object o2, int i, EventSource eventSource)
            throws StaleObjectStateException, LockingStrategyException {
          // No-op
        }
      };

  // Taken from PostgreSQLUUIDJdbcType.java in Hibernate 7.0 and added here as the class didn't
  // exist yet in 6.2
  private static final JdbcType PG_UUID_JDBC_TYPE =
      new UUIDJdbcType() {
        public <X> ValueBinder<X> getBinder(JavaType<X> javaType) {
          return new BasicBinder<>(javaType, this) {
            @Override
            protected void doBindNull(PreparedStatement st, int index, WrapperOptions options)
                throws SQLException {
              st.setNull(index, getJdbcType().getJdbcTypeCode(), "uuid");
            }

            @Override
            protected void doBindNull(CallableStatement st, String name, WrapperOptions options)
                throws SQLException {
              st.setNull(name, getJdbcType().getJdbcTypeCode(), "uuid");
            }

            @Override
            protected void doBind(PreparedStatement st, X value, int index, WrapperOptions options)
                throws SQLException {
              st.setObject(index, getJavaType().unwrap(value, UUID.class, options));
            }

            @Override
            protected void doBind(
                CallableStatement st, X value, String name, WrapperOptions options)
                throws SQLException {
              st.setObject(name, getJavaType().unwrap(value, UUID.class, options));
            }
          };
        }
      };

  @Override
  public boolean supportsTemporaryTables() {
    return false;
  }

  @Override
  public boolean supportsTemporaryTablePrimaryKey() {
    return false;
  }

  @Override
  public boolean dropConstraints() {
    return false;
  }

  @Override
  public boolean supportsAlterColumnType() {
    return false;
  }

  @Override
  public String getTruncateTableStatement(String table) {
    return "delete from " + table;
  }

  @Override
  public Exporter<ForeignKey> getForeignKeyExporter() {
    return NO_FK_SUPPORT_EXPORTER;
  }

  @Override
  public boolean supportsCascadeDelete() {
    return false;
  }

  @Override
  public String getCreateIndexString(boolean unique) {
    return unique ? "create unique index async" : "create index async";
  }

  @Override
  public LockingStrategy getLockingStrategy(Lockable lockable, LockMode lockMode) {
    switch (lockMode) {
      case PESSIMISTIC_FORCE_INCREMENT:
      case UPGRADE_NOWAIT:
      case UPGRADE_SKIPLOCKED:
      case OPTIMISTIC_FORCE_INCREMENT:
      case PESSIMISTIC_READ:
        throw new UnsupportedOperationException("Unsupported lock mode.");
      case PESSIMISTIC_WRITE:
        return new PessimisticWriteSelectLockingStrategy(lockable, lockMode);
      case OPTIMISTIC:
      case READ:
      default:
        return NO_LOCKING_STRATEGY;
    }
  }

  @Override
  public String getForUpdateString(String aliases, LockOptions lockOptions) {
    return " for update";
  }

  @Override
  public String getWriteLockString(int timeout) {
    return " for update";
  }

  @Override
  public String getWriteLockString(String aliases, int timeout) {
    return " for update";
  }

  @Override
  public boolean supportsLockTimeouts() {
    return false;
  }

  @Override
  public int getDefaultDecimalPrecision() {
    return 18;
  }

  @Override
  public int getDoublePrecision() {
    return 15;
  }

  @Override
  public int getFloatPrecision() {
    return 6;
  }

  @Override
  public int getMaxVarcharCapacity() {
    return 65_535;
  }

  @Override
  public int getMaxVarcharLength() {
    return 65_535;
  }

  @Override
  public boolean supportsColumnCheck() {
    return false;
  }

  // Below taken from 7.x PostgreSQLDialect, with some removed 7.x features

  @Override
  public void appendBinaryLiteral(SqlAppender appender, byte[] bytes) {
    appender.appendSql("bytea '\\x");
    PrimitiveByteArrayJavaType.INSTANCE.appendString(appender, bytes);
    appender.appendSql('\'');
  }

  @Override
  public void appendBooleanValueString(SqlAppender appender, boolean bool) {
    appender.appendSql(bool);
  }

  @Override
  public void appendDatetimeFormat(SqlAppender appender, String format) {
    appender.appendSql(datetimeFormat(format).result());
  }

  public Replacer datetimeFormat(String format) {
    return OracleDialect.datetimeFormat(format, true, false)
        .replace("SSSSSS", "US")
        .replace("SSSSS", "US")
        .replace("SSSS", "US")
        .replace("SSS", "MS")
        .replace("SS", "MS")
        .replace("S", "MS")
        // use ISO day in week, as per DateTimeFormatter
        .replace("ee", "ID")
        .replace("e", "fmID")
        // TZR is TZ in Postgres
        .replace("zzz", "TZ")
        .replace("zz", "TZ")
        .replace("z", "TZ")
        .replace("xxx", "OF")
        .replace("xx", "OF")
        .replace("x", "OF");
  }

  @Override
  public void appendDateTimeLiteral(
      SqlAppender appender,
      TemporalAccessor temporalAccessor,
      @SuppressWarnings("deprecation") TemporalType precision,
      TimeZone jdbcTimeZone) {
    switch (precision) {
      case DATE:
        appender.appendSql("date '");
        appendAsDate(appender, temporalAccessor);
        appender.appendSql('\'');
        break;
      case TIME:
        if (supportsTemporalLiteralOffset()
            && temporalAccessor.isSupported(ChronoField.OFFSET_SECONDS)) {
          appender.appendSql("time with time zone '");
          appendAsTime(appender, temporalAccessor, true, jdbcTimeZone);
        } else {
          appender.appendSql("time '");
        }
        appender.appendSql('\'');
        break;
      case TIMESTAMP:
        if (supportsTemporalLiteralOffset()
            && temporalAccessor.isSupported(ChronoField.OFFSET_SECONDS)) {
          appender.appendSql("timestamp with time zone '");
          appendAsTimestampWithMicros(appender, temporalAccessor, true, jdbcTimeZone);
          appender.appendSql('\'');
        } else {
          appender.appendSql("timestamp '");
          appendAsTimestampWithMicros(appender, temporalAccessor, false, jdbcTimeZone);
          appender.appendSql('\'');
        }
        break;
      default:
        throw new IllegalArgumentException();
    }
  }

  @Override
  public void appendDateTimeLiteral(
      SqlAppender appender,
      Date date,
      @SuppressWarnings("deprecation") TemporalType precision,
      TimeZone jdbcTimeZone) {
    switch (precision) {
      case DATE:
        appender.appendSql("date '");
        appendAsDate(appender, date);
        appender.appendSql('\'');
        break;
      case TIME:
        appender.appendSql("time with time zone '");
        appendAsTime(appender, date, jdbcTimeZone);
        appender.appendSql('\'');
        break;
      case TIMESTAMP:
        appender.appendSql("timestamp with time zone '");
        appendAsTimestampWithMicros(appender, date, jdbcTimeZone);
        appender.appendSql('\'');
        break;
      default:
        throw new IllegalArgumentException();
    }
  }

  @Override
  public void appendDateTimeLiteral(
      SqlAppender appender,
      Calendar calendar,
      @SuppressWarnings("deprecation") TemporalType precision,
      TimeZone jdbcTimeZone) {
    switch (precision) {
      case DATE:
        appender.appendSql("date '");
        appendAsDate(appender, calendar);
        appender.appendSql('\'');
        break;
      case TIME:
        appender.appendSql("time with time zone '");
        appendAsTime(appender, calendar, jdbcTimeZone);
        appender.appendSql('\'');
        break;
      case TIMESTAMP:
        appender.appendSql("timestamp with time zone '");
        appendAsTimestampWithMillis(appender, calendar, jdbcTimeZone);
        appender.appendSql('\'');
        break;
      default:
        throw new IllegalArgumentException();
    }
  }

  @Override
  public String castPattern(CastType from, CastType to) {
    if (from == CastType.STRING && to == CastType.BOOLEAN) {
      return "cast(?1 as ?2)";
    } else {
      return super.castPattern(from, to);
    }
  }

  @Override
  public String currentTime() {
    return "localtime";
  }

  @Override
  public String currentTimestamp() {
    return "localtimestamp";
  }

  @Override
  public String currentTimestampWithTimeZone() {
    return "current_timestamp";
  }

  /**
   * The {@code extract()} function returns {@link TemporalUnit#DAY_OF_WEEK} numbered from 0 to 6.
   * This isn't consistent with what most other databases do, so here we adjust the result by
   * generating {@code (extract(dow,arg)+1))}.
   */
  @Override
  public String extractPattern(TemporalUnit unit) {
    return switch (unit) {
      case DAY_OF_WEEK -> "(" + super.extractPattern(unit) + "+1)";
      default -> super.extractPattern(unit);
    };
  }

  @Override
  public AggregateSupport getAggregateSupport() {
    return PostgreSQLAggregateSupport.valueOf(this);
  }

  @Override
  public String getCascadeConstraintsString() {
    return " cascade";
  }

  @Override
  public String getCaseInsensitiveLike() {
    return "ilike";
  }

  @Override
  public String getCurrentSchemaCommand() {
    return "select current_schema()";
  }

  @Override
  public String getCurrentTimestampSelectString() {
    return "select now()";
  }

  @Override
  public int getDefaultStatementBatchSize() {
    return 15;
  }

  /**
   * {@code microsecond} is the smallest unit for an {@code interval}, and the highest precision for
   * a {@code timestamp}, so we could use it as the "native" precision, but it's more convenient to
   * use whole seconds (with the fractional part), since we want to use {@code extract(epoch from
   * ...)} in our emulation of {@code timestampdiff()}.
   */
  @Override
  public long getFractionalSecondPrecisionInNanos() {
    return 1_000_000_000; // seconds
  }

  @Override
  public SelectItemReferenceStrategy getGroupBySelectItemReferenceStrategy() {
    return SelectItemReferenceStrategy.POSITION;
  }

  @Override
  public LimitHandler getLimitHandler() {
    return OffsetFetchLimitHandler.INSTANCE;
  }

  @Override
  public int getMaxIdentifierLength() {
    return 63;
  }

  @Override
  public NameQualifierSupport getNameQualifierSupport() {
    return NameQualifierSupport.SCHEMA;
  }

  @Override
  public NationalizationSupport getNationalizationSupport() {
    return NationalizationSupport.IMPLICIT;
  }

  @Override
  public ResultSet getResultSet(CallableStatement ps) throws SQLException {
    ps.execute();
    return (ResultSet) ps.getObject(1);
  }

  @Override
  public ResultSet getResultSet(CallableStatement statement, int position) throws SQLException {
    if (position != 1) {
      throw new UnsupportedOperationException(
          "PostgreSQL only supports REF_CURSOR parameters as the first parameter");
    }
    return (ResultSet) statement.getObject(1);
  }

  @Override
  public ResultSet getResultSet(CallableStatement statement, String name) throws SQLException {
    throw new UnsupportedOperationException(
        "PostgreSQL only supports accessing REF_CURSOR parameters by position");
  }

  @Override
  public String getSelectClauseNullString(int sqlType, TypeConfiguration typeConfiguration) {
    return "cast(null as "
        + typeConfiguration.getDdlTypeRegistry().getDescriptor(sqlType).getRawTypeName()
        + ")";
  }

  @Override
  public TimeZoneSupport getTimeZoneSupport() {
    return TimeZoneSupport.NORMALIZE;
  }

  private final UniqueDelegate uniqueDelegate = new CreateTableUniqueDelegate(this);

  @Override
  public UniqueDelegate getUniqueDelegate() {
    return uniqueDelegate;
  }

  @Override
  public boolean isCurrentTimestampSelectStringCallable() {
    return false;
  }

  @Override
  public boolean qualifyIndexName() {
    return false;
  }

  @Override
  public int registerResultSetOutParameter(CallableStatement statement, int col)
      throws SQLException {
    // Register the type of the out param - PostgreSQL uses Types.OTHER
    statement.registerOutParameter(col++, Types.OTHER);
    return col;
  }

  @Override
  public boolean requiresParensForTupleDistinctCounts() {
    return true;
  }

  @Override
  public JdbcType resolveSqlTypeDescriptor(
      String columnTypeName,
      int jdbcTypeCode,
      int precision,
      int scale,
      JdbcTypeRegistry jdbcTypeRegistry) {
    switch (jdbcTypeCode) {
      case OTHER:
        switch (columnTypeName) {
          case "uuid":
            jdbcTypeCode = UUID;
            break;
          case "json":
          case "jsonb":
            jdbcTypeCode = JSON;
            break;
          case "xml":
            jdbcTypeCode = SQLXML;
            break;
          case "inet":
            jdbcTypeCode = INET;
            break;
          case "geometry":
            jdbcTypeCode = GEOMETRY;
            break;
          case "geography":
            jdbcTypeCode = GEOGRAPHY;
            break;
        }
        break;
      case TIME:
        // The PostgreSQL JDBC driver reports TIME for timetz, but we use it only for mapping
        // OffsetTime to UTC
        if ("timetz".equals(columnTypeName)) {
          jdbcTypeCode = TIME_UTC;
        }
        break;
      case TIMESTAMP:
        // The PostgreSQL JDBC driver reports TIMESTAMP for timestamptz, but we use it only for
        // mapping Instant
        if ("timestamptz".equals(columnTypeName)) {
          jdbcTypeCode = TIMESTAMP_UTC;
        }
        break;
    }
    return jdbcTypeRegistry.getDescriptor(jdbcTypeCode);
  }

  @Override
  public boolean supportsCaseInsensitiveLike() {
    return true;
  }

  @Override
  public boolean supportsCommentOn() {
    return true;
  }

  @Override
  public boolean supportsCurrentTimestampSelection() {
    return true;
  }

  @Override
  public boolean supportsDistinctFromPredicate() {
    return true;
  }

  @Override
  public boolean supportsFetchClause(FetchClauseType type) {
    return switch (type) {
      case ROWS_ONLY -> true;
      case PERCENT_ONLY, PERCENT_WITH_TIES -> false;
      case ROWS_WITH_TIES -> true;
    };
  }

  @Override
  public boolean supportsIfExistsAfterAlterTable() {
    return true;
  }

  @Override
  public boolean supportsIfExistsBeforeConstraintName() {
    return true;
  }

  @Override
  public boolean supportsIfExistsBeforeTableName() {
    return true;
  }

  @Override
  public boolean supportsIfExistsBeforeTypeName() {
    return true;
  }

  @Override
  public boolean supportsJdbcConnectionLobCreation(DatabaseMetaData databaseMetaData) {
    return false;
  }

  @Override
  public boolean supportsLateral() {
    return true;
  }

  @Override
  public boolean supportsLobValueChangePropagation() {
    return false;
  }

  @Override
  public boolean supportsMaterializedLobAccess() {
    // Prefer using text and bytea over oid (LOB), because oid is very restricted.
    // If someone really wants a type bigger than 1GB, they should ask for it by using @Lob
    // explicitly
    return false;
  }

  @Override
  public boolean supportsOffsetInSubquery() {
    return true;
  }

  @Override
  public boolean supportsOuterJoinForUpdate() {
    return false;
  }

  @Override
  public boolean supportsTemporalLiteralOffset() {
    return true;
  }

  @Override
  public boolean supportsTupleCounts() {
    return true;
  }

  @Override
  public boolean supportsUnboundedLobLocatorMaterialization() {
    return false;
  }

  @Override
  public boolean supportsValuesList() {
    return true;
  }

  @Override
  public boolean supportsWait() {
    return false;
  }

  @Override
  public boolean supportsWindowFunctions() {
    return true;
  }

  @Override
  public String timestampaddPattern(
      TemporalUnit unit, TemporalType temporalType, IntervalType intervalType) {
    return intervalType != null
        ? "(?2+?3)"
        : "cast(?3+" + intervalPattern(unit) + " as " + temporalType.name().toLowerCase() + ")";
  }

  private static String intervalPattern(TemporalUnit unit) {
    return switch (unit) {
      case NANOSECOND -> "(?2)/1e3*interval '1 microsecond'";
      case NATIVE -> "(?2)*interval '1 second'";
      case QUARTER -> "(?2)*interval '3 month'"; // quarter is not supported in interval literals
      case WEEK -> "(?2)*interval '7 day'"; // week is not supported in interval literals
      default -> "(?2)*interval '1 " + unit + "'";
    };
  }

  @Override
  public String timestampdiffPattern(
      TemporalUnit unit, TemporalType fromTemporalType, TemporalType toTemporalType) {
    if (unit == null) {
      return "(?3-?2)";
    }
    if (toTemporalType == TemporalType.DATE && fromTemporalType == TemporalType.DATE) {
      // special case: subtraction of two dates
      // results in an integer number of days
      // instead of an INTERVAL
      return switch (unit) {
        case YEAR, MONTH, QUARTER ->
            "extract(" + translateDurationField(unit) + " from age(?3,?2))";
        default -> "(?3-?2)" + DAY.conversionFactor(unit, this);
      };
    } else {
      return switch (unit) {
        case YEAR -> "extract(year from ?3-?2)";
        case QUARTER -> "(extract(year from ?3-?2)*4+extract(month from ?3-?2)/3)";
        case MONTH -> "(extract(year from ?3-?2)*12+extract(month from ?3-?2))";
        case WEEK ->
            "(extract(day from ?3-?2)/7)"; // week is not supported by extract() when the argument
          // is a duration
        case DAY -> "extract(day from ?3-?2)";
          // in order to avoid multiple calls to extract(),
          // we use extract(epoch from x - y) * factor for
          // all the following units:
        case HOUR, MINUTE, SECOND, NANOSECOND, NATIVE ->
            "extract(epoch from ?3-?2)" + EPOCH.conversionFactor(unit, this);
        default -> throw new SemanticException("Unrecognized field: " + unit);
      };
    }
  }

  @Override
  public String translateExtractField(TemporalUnit unit) {
    return switch (unit) {
        // WEEK means the ISO week number on Postgres
      case DAY_OF_MONTH -> "day";
      case DAY_OF_YEAR -> "doy";
      case DAY_OF_WEEK -> "dow";
      default -> super.translateExtractField(unit);
    };
  }

  @Override
  public boolean useInputStreamToInsertBlob() {
    return false;
  }

  @Override
  public void contributeTypes(
      TypeContributions typeContributions, ServiceRegistry serviceRegistry) {
    super.contributeTypes(typeContributions, serviceRegistry);
    contributePostgreSQLTypes(typeContributions, serviceRegistry);
  }

  /** Allow for extension points to override this only */
  protected void contributePostgreSQLTypes(
      TypeContributions typeContributions, ServiceRegistry serviceRegistry) {
    final JdbcTypeRegistry jdbcTypeRegistry =
        typeContributions.getTypeConfiguration().getJdbcTypeRegistry();
    // For discussion of BLOB support in Postgres, as of 8.4, see:
    //     http://jdbc.postgresql.org/documentation/84/binary-data.html
    // For how this affects Hibernate, see:
    //     http://in.relation.to/15492.lace

    // Force BLOB binding.  Otherwise, byte[] fields annotated
    // with @Lob will attempt to use
    // BlobTypeDescriptor.PRIMITIVE_ARRAY_BINDING.  Since the
    // dialect uses oid for Blobs, byte arrays cannot be used.
    jdbcTypeRegistry.addDescriptor(BLOB, BlobJdbcType.BLOB_BINDING);
    jdbcTypeRegistry.addDescriptor(CLOB, ClobJdbcType.CLOB_BINDING);
    // Don't use this type due to https://github.com/pgjdbc/pgjdbc/issues/2862
    // jdbcTypeRegistry.addDescriptor( TimestampUtcAsOffsetDateTimeJdbcType.INSTANCE );
    jdbcTypeRegistry.addDescriptor(XmlJdbcType.INSTANCE);

    if (PgJdbcHelper.isUsable(serviceRegistry)) {
      jdbcTypeRegistry.addDescriptorIfAbsent(PgJdbcHelper.getInetJdbcType(serviceRegistry));
      jdbcTypeRegistry.addDescriptorIfAbsent(PgJdbcHelper.getIntervalJdbcType(serviceRegistry));
      jdbcTypeRegistry.addDescriptorIfAbsent(PgJdbcHelper.getStructJdbcType(serviceRegistry));
      jdbcTypeRegistry.addDescriptorIfAbsent(PgJdbcHelper.getJsonbJdbcType(serviceRegistry));
    } else {
      jdbcTypeRegistry.addDescriptorIfAbsent(PostgreSQLCastingInetJdbcType.INSTANCE);
      jdbcTypeRegistry.addDescriptorIfAbsent(PostgreSQLCastingIntervalSecondJdbcType.INSTANCE);
      jdbcTypeRegistry.addDescriptorIfAbsent(PostgreSQLStructCastingJdbcType.INSTANCE);
      jdbcTypeRegistry.addDescriptorIfAbsent(PostgreSQLCastingJsonJdbcType.JSONB_INSTANCE);
    }

    // PostgreSQL requires a custom binder for binding untyped nulls as VARBINARY
    typeContributions.contributeJdbcType(ObjectNullAsBinaryTypeJdbcType.INSTANCE);

    // Until we remove StandardBasicTypes, we have to keep this
    typeContributions.contributeType(
        new JavaObjectType(
            ObjectNullAsBinaryTypeJdbcType.INSTANCE,
            typeContributions
                .getTypeConfiguration()
                .getJavaTypeRegistry()
                .getDescriptor(Object.class)));
    // Modified from original to remove not yet added types from later Hibernate versions, and adds
    // UUID
    jdbcTypeRegistry.addDescriptor(PG_UUID_JDBC_TYPE);
  }

  @Override
  protected String columnType(int sqlTypeCode) {
    return switch (sqlTypeCode) {
        // no tinyint, not even in Postgres 11
      case TINYINT -> "smallint";

        // there are no nchar/nvarchar types in Postgres
      case NCHAR -> columnType(CHAR);
      case NVARCHAR -> columnType(VARCHAR);

        // since there's no real difference between TEXT and VARCHAR,
        // except for the length limit, we can just use 'text' for the
        // "long" string types
      case LONG32VARCHAR, LONG32NVARCHAR -> "text";

        // use oid as the blob/clob type on Postgres because
        // the JDBC driver doesn't allow using bytea/text via
        // LOB APIs
      case BLOB, CLOB, NCLOB -> "oid";

        // use bytea as the "long" binary type (that there is no
        // real VARBINARY type in Postgres, so we always use this)
      case BINARY, VARBINARY, LONG32VARBINARY -> "bytea";

        // We do not use the 'time with timezone' type because PG
        // deprecated it, and it lacks certain operations like
        // subtraction
        //			case TIME_UTC:
        //				return columnType( TIME_WITH_TIMEZONE );

      case TIMESTAMP_UTC -> columnType(TIMESTAMP_WITH_TIMEZONE);

      default -> super.columnType(sqlTypeCode);
    };
  }

  @Override
  protected String castType(int sqlTypeCode) {
    return switch (sqlTypeCode) {
      case CHAR, NCHAR, VARCHAR, NVARCHAR -> "varchar";
      case LONG32VARCHAR, LONG32NVARCHAR -> "text";
      case BINARY, VARBINARY, LONG32VARBINARY -> "bytea";
      default -> super.castType(sqlTypeCode);
    };
  }

  @Override
  protected void registerColumnTypes(
      TypeContributions typeContributions, ServiceRegistry serviceRegistry) {
    super.registerColumnTypes(typeContributions, serviceRegistry);
    final DdlTypeRegistry ddlTypeRegistry =
        typeContributions.getTypeConfiguration().getDdlTypeRegistry();

    // Register this type to be able to support Float[]
    // The issue is that the JDBC driver can't handle createArrayOf( "float(24)", ... )
    // It requires the use of "real" or "float4"
    // Alternatively we could introduce a new API in Dialect for creating such base names
    ddlTypeRegistry.addDescriptor(
        CapacityDependentDdlType.builder(FLOAT, columnType(FLOAT), castType(FLOAT), this)
            .withTypeCapacity(6, "float4")
            .withTypeCapacity(15, "float8")
            .build());

    ddlTypeRegistry.addDescriptor(new DdlTypeImpl(SQLXML, "xml", this));
    ddlTypeRegistry.addDescriptor(new DdlTypeImpl(UUID, "uuid", this));
    ddlTypeRegistry.addDescriptor(new DdlTypeImpl(INET, "inet", this));
    ddlTypeRegistry.addDescriptor(new DdlTypeImpl(GEOMETRY, "geometry", this));
    ddlTypeRegistry.addDescriptor(new DdlTypeImpl(GEOGRAPHY, "geography", this));
    ddlTypeRegistry.addDescriptor(new Scale6IntervalSecondDdlType(this));

    // Prefer jsonb if possible
    ddlTypeRegistry.addDescriptor(new DdlTypeImpl(JSON, "jsonb", this));
  }

  @Override
  protected Integer resolveSqlTypeCode(String columnTypeName, TypeConfiguration typeConfiguration) {
    return switch (columnTypeName) {
      case "bool" -> Types.BOOLEAN;
      case "float4" ->
          Types.REAL; // Use REAL instead of FLOAT to get Float as recommended Java type
      case "float8" -> Types.DOUBLE;
      case "int2" -> Types.SMALLINT;
      case "int4" -> Types.INTEGER;
      case "int8" -> Types.BIGINT;
      default -> super.resolveSqlTypeCode(columnTypeName, typeConfiguration);
    };
  }

  protected boolean supportsMinMaxOnUuid() {
    return false;
  }

  @Override
  public SqlAstTranslatorFactory getSqlAstTranslatorFactory() {
    return new StandardSqlAstTranslatorFactory() {
      @Override
      protected <T extends JdbcOperation> SqlAstTranslator<T> buildTranslator(
          SessionFactoryImplementor sessionFactory, Statement statement) {
        return new PostgreSQLSqlAstTranslator<T>(sessionFactory, statement) {
          @Override
          protected String getForUpdate() {
            return " for update";
          }
        };
      }
    };
  }

  // Modified from 7.x version to remove unsupported functions in 6.2
  @Override
  public void initializeFunctionRegistry(FunctionContributions functionContributions) {
    super.initializeFunctionRegistry(functionContributions);

    CommonFunctionFactory functionFactory = new CommonFunctionFactory(functionContributions);

    functionFactory.cot();
    functionFactory.radians();
    functionFactory.degrees();
    functionFactory.log();
    functionFactory.mod_operator();
    functionFactory.log10();
    functionFactory.tanh();
    functionFactory.sinh();
    functionFactory.cosh();
    functionFactory.moreHyperbolic();
    functionFactory.cbrt();
    functionFactory.pi();
    functionFactory.trim2();
    functionFactory.repeat();
    functionFactory.initcap();
    functionFactory.substr();
    functionFactory.substring_substr();
    // also natively supports ANSI-style substring()
    functionFactory.translate();
    functionFactory.toCharNumberDateTimestamp();
    functionFactory.concat_pipeOperator("convert_from(lo_get(?1),pg_client_encoding())");
    functionFactory.localtimeLocaltimestamp();
    functionFactory.length_characterLength_pattern("length(lo_get(?1),pg_client_encoding())");
    functionFactory.bitLength_pattern("bit_length(?1)", "length(lo_get(?1))*8");
    functionFactory.octetLength_pattern("octet_length(?1)", "length(lo_get(?1))");
    functionFactory.ascii();
    functionFactory.char_chr();
    functionFactory.position();
    functionFactory.bitandorxornot_operator();
    functionFactory.bitAndOr();
    functionFactory.everyAny_boolAndOr();
    functionFactory.median_percentileCont(false);
    functionFactory.stddev();
    functionFactory.stddevPopSamp();
    functionFactory.variance();
    functionFactory.varPopSamp();
    functionFactory.covarPopSamp();
    functionFactory.corr();
    functionFactory.regrLinearRegressionAggregates();
    functionFactory.insert_overlay();
    functionFactory.overlay();
    functionFactory.soundex(); // was introduced in Postgres 9 apparently

    functionFactory.locate_positionSubstring();
    functionFactory.windowFunctions();
    functionFactory.listagg_stringAgg("varchar");

    functionFactory.makeDateTimeTimestamp();
    // Note that PostgreSQL doesn't support the OVER clause for ordered set-aggregate functions
    functionFactory.inverseDistributionOrderedSetAggregates();
    functionFactory.hypotheticalOrderedSetAggregates();

    if (!supportsMinMaxOnUuid()) {
      functionContributions
          .getFunctionRegistry()
          .register("min", new PostgreSQLMinMaxFunction("min"));
      functionContributions
          .getFunctionRegistry()
          .register("max", new PostgreSQLMinMaxFunction("max"));
    }

    // Postgres uses # instead of ^ for XOR
    functionContributions
        .getFunctionRegistry()
        .patternDescriptorBuilder("bitxor", "(?1#?2)")
        .setExactArgumentCount(2)
        .setArgumentTypeResolver(
            StandardFunctionArgumentTypeResolvers.ARGUMENT_OR_IMPLIED_RESULT_TYPE)
        .register();

    functionContributions
        .getFunctionRegistry()
        .register("round", new PostgreSQLTruncRoundFunction("round", true));
    functionContributions
        .getFunctionRegistry()
        .register(
            "trunc",
            new PostgreSQLTruncFunction(true, functionContributions.getTypeConfiguration()));
    functionContributions.getFunctionRegistry().registerAlternateKey("truncate", "trunc");
    functionFactory.dateTrunc();
  }

  @Override
  public SqmMultiTableMutationStrategy getFallbackSqmMutationStrategy(
      EntityMappingType rootEntityDescriptor,
      RuntimeModelCreationContext runtimeModelCreationContext) {
    return new CteMutationStrategy(rootEntityDescriptor, runtimeModelCreationContext);
  }

  @Override
  public SqmMultiTableInsertStrategy getFallbackSqmInsertStrategy(
      EntityMappingType rootEntityDescriptor,
      RuntimeModelCreationContext runtimeModelCreationContext) {
    return new CteInsertStrategy(rootEntityDescriptor, runtimeModelCreationContext);
  }

  @Override
  public boolean supportsNonQueryWithCTE() {
    return true;
  }

  @Override
  public DmlTargetColumnQualifierSupport getDmlTargetColumnQualifierSupport() {
    return DmlTargetColumnQualifierSupport.TABLE_ALIAS;
  }
}
