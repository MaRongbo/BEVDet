# Copyright (c) Phigent Robotics. All rights reserved.

_base_ = ['../_base_/datasets/nus-3d.py',
          '../_base_/default_runtime.py']
# Global
# If point cloud range is changed, the models should also change their point
# cloud range accordingly
# For nuScenes we usually do 10-class detection

input_modality = dict(use_lidar=False, use_camera=True)
point_cloud_range = [-51.2, -51.2, -5.0, 51.2, 51.2, 3.0]
class_names = ['Car', 'Truck']
used_cameras=2
data_config={
    'input_size': (256, 704),
    
    # Augmentation
    'resize': (-0.06, 0.11),
    'rot': (-5.4, 5.4),
    'flip': True,
    'crop_h': (0.0, 0.0),
    'resize_test':0.04,
}

# Model
grid_config={
        'xbound': [-51.2, 51.2, 0.8],
        'ybound': [-51.2, 51.2, 0.8],
        'zbound': [-10.0, 10.0, 20.0],
        'dbound': [1.0, 60.0, 1.0],}

voxel_size = [0.1, 0.1, 0.2]

numC_Trans=64

model = dict(
    type='BEVDet',
    img_backbone=dict(
        pretrained='torchvision://resnet50',
        type='ResNet',
        depth=50,
        num_stages=4,
        out_indices=(2, 3),
        frozen_stages=-1,
        norm_cfg=dict(type='BN', requires_grad=True),
        norm_eval=False,
        with_cp=True,
        style='pytorch'),
    img_neck=dict(
        type='FPNForBEVDet',
        in_channels=[1024, 2048],
        out_channels=512,
        num_outs=1,
        start_level=0,
        out_ids=[0]),
    img_view_transformer=dict(type='ViewTransformerLiftSplatShoot',
                              grid_config=grid_config,
                              data_config=data_config,
                              numC_Trans=numC_Trans),
    img_bev_encoder_backbone = dict(type='ResNetForBEVDet', numC_input=numC_Trans),
    img_bev_encoder_neck = dict(type='FPN_LSS',
                                in_channels=numC_Trans*8+numC_Trans*2,
                                out_channels=256),
    pts_bbox_head=dict(
        type='CenterHead',
        in_channels=256,
        tasks=[
            dict(num_class=1, class_names=['Car']),
            dict(num_class=1, class_names=['Truck']),
        ],
        common_heads=dict(
            reg=(2, 2), height=(1, 2), dim=(3, 2), rot=(2, 2)),
        share_conv_channel=64,
        bbox_coder=dict(
            type='CenterPointBBoxCoder',
            pc_range=point_cloud_range[:2],
            post_center_range=[-61.2, -61.2, -10.0, 61.2, 61.2, 10.0],
            max_num=500,
            score_threshold=0.1,
            out_size_factor=8,
            voxel_size=voxel_size[:2],
            code_size=7),
        separate_head=dict(
            type='SeparateHead', init_bias=-2.19, final_kernel=3),
        loss_cls=dict(type='GaussianFocalLoss', reduction='mean'),
        loss_bbox=dict(type='L1Loss', reduction='mean', loss_weight=0.25),
        norm_bbox=True),
    # model training and testing settings
    train_cfg=dict(
        pts=dict(
            point_cloud_range=point_cloud_range,
            grid_size=[1024, 1024, 40],
            voxel_size=voxel_size,
            out_size_factor=8,
            dense_reg=1,
            gaussian_overlap=0.1,
            max_objs=500,
            min_radius=2,
            code_weights=[1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0])),
    test_cfg=dict(
        pts=dict(
            pc_range=point_cloud_range[:2],
            post_center_limit_range=[-61.2, -61.2, -10.0, 61.2, 61.2, 10.0],
            max_per_img=500,
            max_pool_nms=False,
            min_radius=[4, 12, 10, 1, 0.85, 0.175],
            score_threshold=0.1,
            out_size_factor=8,
            voxel_size=voxel_size[:2],
            # nms_type='circle',
            pre_max_size=1000,
            post_max_size=83,
            # nms_thr=0.2,

            # Scale-NMS
            nms_type=['rotate', 'rotate', 'rotate', 'circle', 'rotate', 'rotate'],
            nms_thr=[0.2, 0.2, 0.2, 0.2, 0.2, 0.5],
            nms_rescale_factor=[1.0, [0.7, 0.7], [0.4, 0.55], 1.1, [1.0, 1.0], [4.5, 9.0]]
        )))


# Data
dataset_type = 'PlusKittiDataset'
l4_data_root = '/home/wancheng.shen/datasets/CN_L4_origin_data/'
l4_benchmark_root = '/home/wancheng.shen/datasets/CN_L4_origin_benchmark/'
l3_data_root = '/mnt/intel/jupyterhub/mrb/datasets/L4E_wo_tele/L4E_origin_data/'
l3_benchmark_root = '/mnt/intel/jupyterhub/swc/datasets/L4E_wo_tele/L4E_origin_benchmark/'
file_client_args = dict(backend='disk')


train_pipeline = [
    dict(type='LoadMultiViewImageFromFiles_Plus', is_train=True, data_config=data_config),
    dict(
        type='LoadPlusPointsFromFile',
        coord_type='LIDAR',
        load_dim=4,
        use_dim=4,
        point_type='float64',
        file_client_args=file_client_args),
    dict(
        type='LoadAnnotations3D',
        with_bbox_3d=True,
        with_label_3d=True,
        file_client_args=file_client_args),
    dict(
        type='GlobalRotScaleTrans',
        rot_range=[-0.3925, 0.3925],
        scale_ratio_range=[0.95, 1.05],
        translation_std=[0, 0, 0],
        update_img2lidar=True),
    dict(
        type='RandomFlip3D',
        sync_2d=False,
        flip_ratio_bev_horizontal=0.5,
        flip_ratio_bev_vertical=0.5,
        update_img2lidar=True),
    dict(type='ObjectRangeFilter', point_cloud_range=point_cloud_range),
    dict(type='ObjectNameFilter', classes=class_names),
    dict(type='DefaultFormatBundle3D', class_names=class_names),
    dict(type='Collect3D', keys=['img_inputs', 'gt_bboxes_3d', 'gt_labels_3d'],
         meta_keys=('filename', 'ori_shape', 'img_shape', 'lidar2img',
                            'depth2img', 'cam2img', 'pad_shape',
                            'scale_factor', 'flip', 'pcd_horizontal_flip',
                            'pcd_vertical_flip', 'box_mode_3d', 'box_type_3d',
                            'img_norm_cfg', 'pcd_trans', 'sample_idx',
                            'pcd_scale_factor', 'pcd_rotation', 'pts_filename',
                            'transformation_3d_flow', 'img_info'))
]

test_pipeline = [
    dict(type='LoadMultiViewImageFromFiles_Plus', is_train=False, data_config=data_config),
    dict(
        type='LoadPlusPointsFromFile',
        coord_type='LIDAR',
        load_dim=4,
        use_dim=4,
        point_type='float64',
        file_client_args=file_client_args),
    dict(
        type='MultiScaleFlipAug3D',
        img_scale=(1333, 800),
        pts_scale_ratio=1,
        flip=False,
        transforms=[
            dict(
                type='DefaultFormatBundle3D',
                class_names=class_names,
                with_label=False),
            # dict(
                # type='PointsRangeFilter', point_cloud_range=point_cloud_range),
            dict(type='Collect3D', keys=['img_inputs', 'points'],
                meta_keys=('filename', 'ori_shape', 'img_shape', 'lidar2img',
                            'depth2img', 'cam2img', 'pad_shape',
                            'scale_factor', 'flip', 'pcd_horizontal_flip',
                            'pcd_vertical_flip', 'box_mode_3d', 'box_type_3d',
                            'img_norm_cfg', 'pcd_trans', 'sample_idx',
                            'pcd_scale_factor', 'pcd_rotation', 'pts_filename',
                            'transformation_3d_flow', 'img_info'))
        ])
]
# construct a pipeline for data and gt loading in show function
# please keep its loading function consistent with test_pipeline (e.g. client)
eval_pipeline = [
    dict(type='LoadMultiViewImageFromFiles_BEVDet', data_config=data_config),
    dict(
        type='DefaultFormatBundle3D',
        class_names=class_names,
        with_label=False),
    dict(type='Collect3D', keys=['img_inputs'])
]

data = dict(
    samples_per_gpu=8,
    workers_per_gpu=8,
    train=dict(
        type='RepeatDataset',
        times=2,
        dataset=dict(
            type=dataset_type,
            data_root=l3_data_root,
            ann_file=l3_data_root + 'Kitti_L4_data_mm3d_infos_train.pkl',
            # ann_file=l3_data_root + 'l4e_mini_data_train.pkl',
            split='training',
            pts_prefix='pointcloud',
            pipeline=train_pipeline,
            modality=input_modality,
            classes=class_names,
            test_mode=False,
            pcd_limit_range=point_cloud_range,
            used_cameras=used_cameras,
            # we use box_type_3d='LiDAR' in kitti and nuscenes dataset
            # and box_type_3d='Depth' in sunrgbd and scannet dataset.
            box_type_3d='LiDAR'
            )),
    val=dict(
        type=dataset_type,
        data_root=l3_data_root,
        ann_file=l3_data_root + 'Kitti_L4_data_mm3d_infos_val.pkl',
        # ann_file=l3_data_root + 'l4e_mini_data_val.pkl',
        split='training',
        pts_prefix='pointcloud',
        pipeline=test_pipeline,
        modality=input_modality,
        classes=class_names,
        test_mode=True,
        pcd_limit_range=point_cloud_range,
        used_cameras=used_cameras,
        box_type_3d='LiDAR'),
    test=dict(
        type=dataset_type,
        data_root=l3_benchmark_root,
        ann_file=l3_benchmark_root + 'Kitti_L4_data_mm3d_infos_val.pkl',
        # data_root=l3_data_root,
        # ann_file=l3_data_root + 'l4e_mini_data_test.pkl',
        split='training',
        pts_prefix='pointcloud',
        samples_per_gpu=8,
        pipeline=test_pipeline,
        modality=input_modality,
        classes=class_names,
        pcd_limit_range=point_cloud_range,
        test_mode=True,
        used_cameras=used_cameras,
        box_type_3d='LiDAR'))

# Optimizer
optimizer = dict(type='AdamW', lr=2e-4, weight_decay=0.01)
optimizer_config = dict(grad_clip=None)
lr_config = dict(
    policy='step',
    warmup='linear',
    warmup_iters=500,
    warmup_ratio=0.001,
    step=[16, 22])
runner = dict(type='EpochBasedRunner', max_epochs=24)


evaluation = dict(interval=10)
checkpoint_config = dict(interval=2)
workflow = [('train', 2), ('val', 1)]