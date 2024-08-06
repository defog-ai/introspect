import { Table, Col, Tooltip } from 'antd';
import { ToolOutlined, RightCircleOutlined } from '@ant-design/icons';
import { useRouter } from 'next/router';

const BasicStatus = ({ loading, metadataUploaded, glossaryUploaded, goldenQueriesUploaded }) => {
  const router = useRouter();
  const dataSource = [
    {
      key: '1',
      status: 'Metadata Updated',
      tooltip: 'Metadata (table names, columns names, column descriptions) updated on Defog',
      value: loading ? '⏳' : metadataUploaded ? '✅' : '❌',
      onClick: () => router.push('/extract-metadata')
    },
    {
      key: '2',
      status: 'Instruction Set Updated',
      tooltip: 'Explicit instructions to guide generation added to Defog',
      value: loading ? '⏳' : glossaryUploaded ? '✅' : '❌',
      onClick: () => router.push('/align-model')
    },
    {
      key: '3',
      status: 'Golden Queries Updated',
      tooltip: 'Golden queries to ground the model\'s generation added to Defog',
      value: loading ? '⏳' : goldenQueriesUploaded ? '✅' : '❌',
      onClick: () => router.push('/align-model')
    }
  ];

  const columns = [
    {
      title: 'Configuration',
      dataIndex: 'status',
      key: 'status',
      render: (text, record) => (
        <>
        <Tooltip title={record.tooltip}>
          <span style={{ cursor: 'pointer' }}>{text}</span>
        </Tooltip>
        <RightCircleOutlined style={{ marginLeft: '0.5em', color: '#1890ff', cursor: 'pointer' }} />
        </>
      ),
      align: 'center',
      width: '50%'
    },
    {
      title: 'Status',
      dataIndex: 'value',
      key: 'value',
      align: 'center', 
      width: '50%'
    },
  ];

  return (
    <Col span={24} style={{ paddingTop: '1em', paddingBottom: '1em'}}>
      <h2 className='text-lg font-semibold'>
        <Tooltip title="Do regular quality checks to keep defog fully customised for databse">
          <ToolOutlined style={{ marginRight: '0.5em', color: '#1890ff', cursor: 'pointer'}} />
        </Tooltip>
        Basic Configuration Status
      </h2>
      <Table 
          style={{ padding: '1.2em' }} 
          dataSource={dataSource} columns={columns} pagination={false} 
          onRow={(record) => ({ onClick: () => record.onClick() })} // Call the onClick handler defined in dataSource
      />
    </Col>
  );
};

export default BasicStatus;
